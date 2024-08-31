## 概述

This is a CLI management tool for acme.sh, which is written in Python.

一款基于Python编写的 acme.sh 多域名管理工具。目前仅集成主要功能，如有扩展功能可直接修改 `src/acme_cli.py` 文件。


---
## QuickStart

> 前提条件: 需要提前准备acme.sh基本环境，详见: [acme.sh实现自动申请证书与自动部署群晖DSM | 环境准备](https://nestealin.com/814887c9/#toc-heading-2)

### 工具下载

本仓库 Release 中已提供 Linux 系统打包好的二进制文件，可以在有限的操作系统中做到"开箱即用"。

```bash
cd /usr/local/acme.sh/scripts
curl -sL https://github.com/nestealin/acme_cli/releases/download/v1.0.0/acme_cli -o acme_cli
chmod +x ./acme_cli
ln -s /usr/local/acme.sh/scripts/acme_cli /usr/local/bin/acme_cli
curl -sL https://github.com/nestealin/acme_cli/releases/download/v1.0.0/domains_config.yaml.sample -o domains_config.yaml
```

### 基本配置

参照 domains_config.yaml 内容，结合域名、NS特性进行修改。

#### 主域名证书

以下是一个 DNS 托管在 Cloudflare，打算申请 example.com 及 *.example.com 域名证书的配置格式:

```yaml
domains:
  # Cloudflare-SingleDomain
  # issue for example.com and *.example.com
  - domain_name: example.com
    domain_ns: dns_cf
    ns_key: CF_Token
    ns_key_value: ABCDEFG1234567890
    ns_secret: CF_Account_ID
    ns_secret_value: HIJKLMN0987654321
    SAN_domains: ""
```

#### 多SAN证书

以下是一个 DNS 托管在 DNSPod，打算申请:
- foo.net
- *.foo.net
- dev.foo.net
- *.dev.foo.net
- test.foo.net
- *.test.foo.net

多SAN域名证书的配置格式:

```yaml
domains:
  # DNSPod-MultiSANs
  # issue for foo.net, *.foo.net, dev.foo.net, *.dev.foo.net, test.foo.net and *.test.foo.net
  - domain_name: foo.net
    domain_ns: dns_dp
    ns_key: DP_Id
    ns_key_value: 123456
    ns_secret: DP_Key
    ns_secret_value: ABCDEFG1234567890
    SAN_domains:
    - dev.foo.net
    - test.foo.net
```


---
## 功能使用

> 前提条件: 
> - 已经安装 acme.sh 基本环境；
> - 已经完成 domains_config.yaml 文件的域名与DNS API配置；

#### 查询当前托管中的证书

```bash
acme_cli list
```

效果:

```bash
# acme_cli list
Main_Domain     KeyLength  SAN_Domains                                                                             CA               Created               Renew
example.com      "ec-256"   *.example.com,*.dev.example.com,*.pre.example.com                                          LetsEncrypt.org  2024-08-30T14:37:23Z  2024-10-28T14:37:23Z
```

#### 续期单一证书

```bash
acme_cli renew ${CERT_DOMAIN}
```

> 注意: 这里的 `CERT_DOMAIN` 指的是证书的主域名，即使用 `acme_cli list` 输出中的 **"Main_Domain"** 字段。

该指令允许使用 `--force` 参数可以实现强制更新，如: 即使当前证书距离到期大于30天，也可以执行强制更新。


#### 更新单一域名

该功能具备如下几种能力:
- 可以是新增域名时的**首次证书申请**；
- 可以是在已有证书的情况下追加SAN域名**重新签发**；
- 可以是对**现有证书执行更新**，效果等同于 `acme_cli renew ${CERT_DOMAIN}`；

```bash
acme_cli issue example.com --force
```

可以增加 `--force` 参数可以实现强制更新，如: 即使当前证书距离到期日期大于30天，也可以执行强制更新。


#### 续期所有证书

```bash
acme_cli renew_all
```

该指令默认为强制更新维护中的所有证书。


---
## 自定义修改

如果现有功能无法满足，可以拉取仓库源码自定义扩展/修改。

环境要求: Python3+

```bash
git clone https://github.com/nestealin/acme_cli.git
cd acme_cli/src
pip install -r requirements.txt
python acme_cli.py list
```

