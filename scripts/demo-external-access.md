# Demo 外网访问指南(Tailscale + Basic Auth)

演示页 `scripts/demo_server.py` 默认绑 `0.0.0.0:8030`,本机 / 同一局域网可直接访问。
要让**不在同一局域网**的人访问,用 Tailscale 组一个私有 VPN,再叠加上层 Basic Auth 口令。
不走公网隧道、不暴露给全网,只限你邀请的人进。

> 为什么不用 ngrok / cloudflared 直接开公网:这个 demo 后面接的是真实 prod-api
> (`192.168.1.239`)、真实设备控制(`real` 模式)和真实 LLM/milvus,页面本身没有鉴权。
> 裸开公网等于让互联网上任何人都能驱动真实设备控制。Tailscale 是私有 VPN,只放行 tailnet 成员。

---

## 0. 前置:访问口令(已在 `.env` 配好)

`.env` 里设了 `DEMO_ACCESS_USER` / `DEMO_ACCESS_PASS`(Basic Auth)。打开页面会弹登录框,
输对才进。把账号密码一并发给要看演示的人。

- **两个变量都得设**,gate 才启用;只设一个不生效,页面仍是开放的。
- 没设这两个变量时,页面开放(本机演示用)。
- 改密码:改 `.env` 这两行,重启服务。
- 口令用你自己的,别用 `.env` 里的内部 service token。

## 1. demo 这台机器装 Tailscale

```bash
winget install tailscale.tailscale
```

或官网下载安装:https://tailscale.com/download/windows
装完登录(Tailscale 账号,个人用免费)。

登录后系统托盘出现 Tailscale 图标。拿这台机器在 tailnet 里的地址:

```bash
tailscale ip -4
```

记下输出的 `100.x.x.x`——这是对方要访问的地址。

## 2. 看演示的人那边也装 Tailscale

对方机器装 Tailscale(https://tailscale.com/download),登录**同一个** Tailscale 账号;
或者你把对方邮箱加进你的 tailnet(管理台 https://login.tailscale.com/admin/users)。
同 tailnet 即可互相看到。

## 3. 启动 demo

```bash
python scripts/demo_server.py
```

已绑 `0.0.0.0`,Tailscale 虚拟网卡自动覆盖,不用额外配置。
(端口可用 `DEMO_PORT` 改,默认 8030。)

## 4. 对方访问

对方浏览器打开(把 `100.x.x.x` 换成第 1 步拿到的地址):

```
http://100.x.x.x:8030
```

弹出 Basic Auth 登录框,输入 `.env` 里的账号密码,进页面。

---

## 注意事项

- **私有 VPN**:只限你邀请进 tailnet 的人访问,不是对公网开放。
- **真实设备控制**:demo 后面是真实 prod-api + `real` 模式。控制类操作有确认卡片,
  但点「确认」会**真下发** `deviceCtrl` / `doorControl`——演示时别误确认。
- **数据令牌**:数据查询(设备 / 工单 / 告警 / 停车 / 餐饮 / 会议)需要页面右侧
  「数据令牌(传后端)」框里粘真实前端登录 JWT,否则 prod-api 报「登录态已失效」。
  知识问答(走 milvus)和页面本身不需要这个令牌。
- 用完直接关 demo 服务即可;Tailscale 常驻无妨。

## 一定要公网链接?(不推荐)

用 **Cloudflare Tunnel + Cloudflare Access**:cloudflared 开隧道拿到公网域名,
Cloudflare Access 在前面加 Google / 邮箱验证码登录。需要 Cloudflare 账号 + cloudflared,
且**隧道命令由你自己运行**。这套是带认证的公网入口,比裸 ngrok 安全。
