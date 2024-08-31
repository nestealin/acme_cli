#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# Author: nestealin
# Created: 2024/08/29

import os
import subprocess
import yaml
import sys
import argparse
import shutil
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from abc import ABC, abstractmethod
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


ACME_HOME: str = "/usr/local/acme.sh"
ACME_SSL_CERT_PATH: str = f"{ACME_HOME}/data"
DOMAINS_CONFIG_PATH: str = f"{ACME_HOME}/scripts"
CONFIG_FILE: str = f"{DOMAINS_CONFIG_PATH}/domains_config.yaml"

class CertificateManager(ABC):
    @abstractmethod
    def issue(self, domain_name, force=False):
        pass

    @abstractmethod
    def renew(self, domain_name, force=False):
        pass

    @abstractmethod
    def remove(self, domain_name, force=False):
        pass

    @abstractmethod
    def list_all(self):
        pass

class AcmeCertificateManager(CertificateManager):
    def __init__(self, acme_home, config_file):
        self.acme_home = acme_home
        self.config_file = config_file

    def issue(self, domain_name, force=False):
        if not force and not self._confirm_action(f"Issue certificate for {domain_name}?"):
            logger.info("Operation cancelled.")
            return

        config = self._load_config()
        domain_config = next((d for d in config['domains'] if d['domain_name'] == domain_name), None)
        if not domain_config:
            logger.error(f"Error: Domain '{domain_name}' not found in the configuration file.")
            return

        self._issue_cert(domain_config, force)

    def renew(self, domain_name, force=False):
        if not self._validate_domain(domain_name):
            return

        ssl_cert_path = os.path.join(ACME_SSL_CERT_PATH, f"{domain_name}_ecc")
        if not os.path.isdir(ssl_cert_path):
            logger.error(f"Certificate directory for {domain_name} does not exist.")
            return

        logger.info(f"Attempting to renew certificate for {domain_name}...")
        self._renew_ssl_cert(domain_name, force)

    def remove(self, domain_name, force=False):
        ssl_cert_path = os.path.join(ACME_SSL_CERT_PATH, f"{domain_name}_ecc")
        
        # Validate the path to prevent accidental deletion of important directories
        if not os.path.normpath(ssl_cert_path).startswith(os.path.normpath(ACME_SSL_CERT_PATH)):
            logger.error(f"Invalid certificate path: {ssl_cert_path}")
            return

        if not force and not self._confirm_action(f"Remove certificate for {domain_name}?"):
            logger.info("Operation cancelled.")
            return

        remove_status = subprocess.run([f"{self.acme_home}/acme.sh", "--remove", "-d", domain_name], capture_output=True, text=True)
        if remove_status.returncode == 0:
            try:
                # Use shutil.rmtree instead of subprocess.run for directory removal
                shutil.rmtree(ssl_cert_path)
                logger.info(f"{domain_name}'s SSL cert has been removed successfully.")
                self.list_all()
            except Exception as e:
                logger.error(f"Error removing certificate directory: {e}")
        else:
            logger.error(f"Operation interrupted: {remove_status.stderr}")

    def list_all(self):
        subprocess.run([f"{self.acme_home}/acme.sh", "list"])

    def _issue_cert(self, domain_config, force):
        domain_name = domain_config['domain_name']
        domain_ns = domain_config.get('domain_ns')
        ns_key = domain_config.get('ns_key')
        ns_key_value = domain_config.get('ns_key_value')
        ns_secret = domain_config.get('ns_secret')
        ns_secret_value = domain_config.get('ns_secret_value')
        san_domains = ' '.join(domain_config.get('SAN_domains', []))

        account_config_file = os.path.join(self.acme_home, "account.conf")
        self._update_account_config(account_config_file, ns_key, ns_key_value, ns_secret, ns_secret_value)

        params = self._build_cert_params(domain_name, san_domains)
        
        # Load environment variables
        subprocess.run(f"source {self.acme_home}/acme.sh.env", shell=True, executable='/bin/bash')
        
        # Upgrade acme.sh
        subprocess.run([f"{self.acme_home}/acme.sh", "--upgrade"], check=True)
        
        cmd_template = f"{self.acme_home}/acme.sh --issue --force --dns {domain_ns} -d {domain_name} {params}"
        logger.debug(f"Executing command: {cmd_template}")
        
        try:
            result = subprocess.run(cmd_template, shell=True, check=True, capture_output=True, text=True)
            logger.info(f"Certificate issuance successful: {result.stdout}")
            self._display_cert_info(domain_name)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error issuing certificate: {e.stderr}")

    def _renew_ssl_cert(self, cert_domain, force=False):
        try:
            cert_file = os.path.join(ACME_SSL_CERT_PATH, f"{cert_domain}_ecc", "fullchain.cer")
            
            # Load environment variables
            subprocess.run(f"source {self.acme_home}/acme.sh.env", shell=True, executable='/bin/bash')
            
            # Upgrade acme.sh
            subprocess.run([f"{self.acme_home}/acme.sh", "--upgrade"], check=True)
            
            renew_cmd = [f"{self.acme_home}/acme.sh", "--renew", "-d", cert_domain]
            if force:
                renew_cmd.append("--force")
            
            renew_status = subprocess.run(renew_cmd, capture_output=True, text=True)
            if renew_status.returncode == 0:
                logger.info(f"Certificate renewal successful: {renew_status.stdout}")
                self._display_cert_info(cert_domain)
            else:
                logger.error(f"Error renewing certificate: {renew_status.stderr}")
        except Exception as e:
            logger.error(f"Error during certificate renewal: {e}")

    def _load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            sys.exit(1)

    def _confirm_action(self, message):
        return input(f"{message} (y/n): ").lower() in ['y', '']

    def _update_account_config(self, config_file, ns_key, ns_key_value, ns_secret, ns_secret_value):
        ns_key_config = f"export {ns_key}={ns_key_value}"
        ns_secret_config = f"export {ns_secret}={ns_secret_value}"

        self._append_to_file_if_not_exists(config_file, ns_key_config)
        self._append_to_file_if_not_exists(config_file, ns_secret_config)

        # Note: 'source' is a shell built-in, not available directly in Python
        # Consider using a shell=True subprocess call if this is absolutely necessary
        logger.debug("Reloading environment variables (Note: this may not affect the current Python process)")
        os.system(f"source {config_file}")

    def _append_to_file_if_not_exists(self, file_path, text):
        with open(file_path, 'r+') as f:
            content = f.read()
            if text not in content:
                f.write(f"{text}\n")
                logger.info(f"{text} added to the environment file.")
            else:
                logger.info(f"{text} already exists, no action taken.")

    def _build_cert_params(self, domain_name, san_domains):
        wildcard_domains = [f"*.{domain_name}"]
        params = [f" -d *.{domain_name}"]

        if san_domains:
            san_list = san_domains.split()
            for san_domain in san_list:
                wildcard_domain = f"*.{san_domain}"
                wildcard_domains.append(wildcard_domain)
                params.append(f" -d {wildcard_domain}")

            for san_domain in san_list:
                if not self._is_wildcard_including(wildcard_domains, san_domain):
                    params.append(f" -d {san_domain}")

        return ''.join(params)

    def _is_wildcard_including(self, wildcard_domains, domain):
        domain_parts = domain.split('.')
        logger.debug(f"Checking domain: {domain}")
        root_domain = domain
        if len(domain_parts) > 2:
            root_domain = '.'.join(domain_parts[1:])
        logger.debug(f"Root domain: {root_domain}")
        wildcard_domain_names = []
        for wildcard_domain in wildcard_domains:
            wildcard_domain_names.append('.'.join(wildcard_domain.split('*.')[1:]))
        logger.debug(f"Wildcard domain names: {wildcard_domain_names}")
        if root_domain in wildcard_domain_names:
            return True
        return False

    def _get_cert_days_left(self, cert_file):
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
            certificate = x509.load_pem_x509_certificate(cert_data, default_backend())

        not_after = certificate.not_valid_after
        expire_date = not_after.replace(tzinfo=timezone.utc).timestamp()
        current_date = datetime.now(timezone.utc).timestamp()

        return int((expire_date - current_date) / 86400)

    def _display_cert_info(self, domain_name):
        cert_file = os.path.join(ACME_SSL_CERT_PATH, f"{domain_name}_ecc", "fullchain.cer")
        if os.path.exists(cert_file):
            days_left = self._get_cert_days_left(cert_file)
            logger.info(f"Certificate for {domain_name} will expire in {days_left} days.")
        else:
            logger.warning(f"Certificate file not found for {domain_name}")

    def _get_existing_domains(self):
        result = subprocess.run([f"{self.acme_home}/acme.sh", "list", "--listraw"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error getting existing domains: {result.stderr}")
            return []
        
        domains = []
        for line in result.stdout.split('\n')[1:]:  # Skip header line
            if line.strip():
                domains.append(line.split('|')[0])
        return domains

    def _validate_domain(self, domain_name):
        config = self._load_config()
        configured_domains = [d['domain_name'] for d in config['domains']]
        existing_domains = self._get_existing_domains()

        if domain_name not in configured_domains:
            logger.warning(f"Domain '{domain_name}' is not in the configuration file. Please add it before renewing.")
            return False
        
        if domain_name not in existing_domains:
            logger.warning(f"Domain '{domain_name}' does not have an existing certificate. Please issue it first.")
            return False
        
        return True

    def renew_all(self, force=False):
        logger.info("Attempting to renew all certificates...")
        try:
            # Load environment variables
            subprocess.run(f"source {self.acme_home}/acme.sh.env", shell=True, executable='/bin/bash')
            
            # Upgrade acme.sh
            subprocess.run([f"{self.acme_home}/acme.sh", "--upgrade"], check=True)
            
            # Renew all certificates
            renew_cmd = [f"{self.acme_home}/acme.sh", "--renew-all", "--ecc", "--force"]
            # if force:
                # renew_cmd.append("--force")
            
            renew_status = subprocess.run(renew_cmd, capture_output=True, text=True)
            if renew_status.returncode == 0:
                logger.info(f"All certificates renewed successfully: {renew_status.stdout}")
                self.list_all()
            else:
                logger.error(f"Error renewing certificates: {renew_status.stderr}")
        except Exception as e:
            logger.error(f"Error during certificate renewal: {e}")

def main():
    parser = argparse.ArgumentParser(description="ACME Certificate Management CLI")
    parser.add_argument("command", choices=["issue", "renew", "remove", "list", "renew_all"],
                        help="Command to execute")
    parser.add_argument("domain", nargs="?", help="Domain name for the certificate")
    parser.add_argument("--force", action="store_true", help="Force the operation without confirmation")

    args = parser.parse_args()

    cert_manager = AcmeCertificateManager(ACME_HOME, CONFIG_FILE)

    if args.command == "list":
        cert_manager.list_all()
    elif args.command == "renew_all":
        cert_manager.renew_all(args.force)
    elif args.domain:
        if args.command == "issue":
            cert_manager.issue(args.domain, args.force)
        elif args.command == "renew":
            cert_manager.renew(args.domain, args.force)
        elif args.command == "remove":
            cert_manager.remove(args.domain, args.force)
    else:
        logger.error(f"Error: The '{args.command}' command requires a domain parameter.")
        sys.exit(1)

if __name__ == "__main__":
    main()
