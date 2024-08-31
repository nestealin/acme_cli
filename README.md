## 概述

This is a CLI management tool for acme.sh, which is written in Python.

一款基于Python编写的 acme.sh 多域名管理工具。目前仅集成主要功能，如有扩展功能可直接修改 `src/acme_cli.py` 文件。


---
## QuickStart

> 前提条件: 需要提前准备acme.sh基本环境，详见: [acme.sh多域名自动化统一管理 | 环境准备](https://nestealin.com/450bd21e/#toc-heading-2)

### 工具下载

在[本仓库 Release](https://github.com/nestealin/acme_cli/releases) 中已提供 Linux 系统打包好的二进制文件，可以在有限的操作系统中做到"开箱即用"。

```bash
mkdir /usr/local/acme.sh/scripts
cd /usr/local/acme.sh/scripts
curl -sL https://github.com/nestealin/acme_cli/releases/download/v1.0.0/acme_cli -o acme_cli
chmod +x ./acme_cli
ln -s /usr/local/acme.sh/scripts/acme_cli /usr/local/bin/acme_cli
curl -sL https://github.com/nestealin/acme_cli/releases/download/v1.0.0/domains_config.yaml.sample -o domains_config.yaml
```



### 基本配置

参照 domains_config.yaml 内容，结合域名、NS特性进行修改。

```bash
cd /usr/local/acme.sh/scripts
vim domains_config.yaml
```

#### 主域名证书

以下是一个 example.com 域名将 DNS 托管在 Cloudflare，打算申请 `example.com` 及 `*.example.com` 域名证书的配置格式:

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

参数释义:

- `domain_name`: 证书主域名，即主要签发的域名，默认签发三级泛域名 `*.foo.org`；
- `domain_ns`: 主域名所属 DNS 服务商，语法格式遵循[acme.sh DNS API 简称](https://nestealin.com/89bbe3ef/#toc-heading-35)；
- `ns_key`: DNS API 参数环境变量"Key"名称，遵循[acme.sh DNS API 变量](https://nestealin.com/89bbe3ef/#toc-heading-35)；
- `ns_key_value`: DNS API 参数环境变量"Key"对应值；
- `ns_secret`: DNS API 参数环境变量"Secret"名称，遵循[acme.sh DNS API 变量](https://nestealin.com/89bbe3ef/#toc-heading-35)；
- `ns_secret_value`: DNS API 参数环境变量"Secret"对应值
- `SAN_domains`: 证书是否需要签发多个子域名，如果不存在则保持 `""` 即可，如果存在则以列表格式追加；



#### 多SAN证书

以下是一个主域名为 foo.net，其 DNS 托管在 DNSPod，打算申请:

- `foo.net`
- `*.foo.net`
- `dev.foo.net`
- `*.dev.foo.net`
- `test.foo.net`
- `*.test.foo.net`

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

> 注: 
> - 更多供应商配置信息请参考: [自动 DNS API 简称及变量速查 | Nes的草稿箱](https://nestealin.com/89bbe3ef/#toc-heading-35)



---

## 基本功能

> 前提条件:
>
> - 已经安装 acme.sh 基本环境；
> - 已经完成 domains_config.yaml 文件的域名与DNS API配置；

以下，将主要介绍二进制工具的管理功能。

#### 查询当前托管中的证书

```shell
acme_cli list
```

效果:

```shell
# acme_cli list
Main_Domain     KeyLength  SAN_Domains                                                                             CA               Created               Renew
example.com      "ec-256"   *.example.com,*.dev.example.com,*.pre.example.com                                          LetsEncrypt.org  2024-08-30T14:37:23Z  2024-10-28T14:37:23Z
```



#### 续期单一证书

```shell
acme_cli renew ${CERT_DOMAIN}
```

> 注意: 这里的 `CERT_DOMAIN` 指的是证书的主域名，即使用 `acme_cli list` 输出中的 **"Main_Domain"** 字段。

该指令允许使用 `--force` 参数可以实现强制更新，如: 即使当前证书距离到期大于30天，也可以执行强制更新。



#### 更新单一域名 | 新增 SAN 域名

该功能具备如下几种能力:

- 可以是新增域名时的**首次证书申请**；
- 可以是在已有证书的情况下追加SAN域名**重新签发**；
- 可以是对**现有证书执行更新**，效果等同于 `acme_cli renew ${CERT_DOMAIN}`；

```shell
acme_cli issue example.com --force
```

可以增加 `--force` 参数可以实现强制更新，如: 即使当前证书距离到期日期大于30天，也可以执行强制更新。



#### 续期所有证书

```shell
acme_cli renew_all
```

该指令默认为强制更新维护中的所有证书。



#### 移除证书

```bash
acme_cli remove example.com
```

该功能会同时移除 acme.sh 维护中的证书，以及本地证书目录，避免需要人为二次清理。（因为删除操作是高危操作，所以会有二次确认的交互内容）



> 注: 由于该工具只是根据笔者习惯简单封装了 acme.sh 的几个常用核心功能，如有自定义扩展需求，可以拉取[仓库源码](https://github.com/nestealin/acme_cli?tab=readme-ov-file#%E8%87%AA%E5%AE%9A%E4%B9%89%E4%BF%AE%E6%94%B9)自定义扩展/修改。




---
## 自定义修改

如果现有功能无法满足，可以拉取仓库源码自定义扩展/修改。

环境要求: Python 3

```bash
git clone https://github.com/nestealin/acme_cli.git
cd acme_cli/src
pip install -r requirements.txt
python acme_cli.py list
```

