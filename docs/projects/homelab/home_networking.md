---
tags:
  - WIP
  - projects
  - networking
created: 2024-07-26
---

# Home Networking setup

This page will outline my networking setup at home, building deploying a homemade router, replacing the one provided from my ISP.

## Parts breakdown

| Item                                                         | Price  | Date Purchased |
| ------------------------------------------------------------ | ------ | -------------- |
| XCY Firewall Mini PC, Intel Celeron N2830, 4GB RAM, 32GB SSD | 136.14 | 24-07-15       |
| Ubiquiti Unifi U6 Long Range                                 |        |                |
| 24-Port gigabit switch                                       |        |                |
| 4-port gigabit PoE+                                          |        |                |

I grabbed a fairly budget secondary switch as I needed PoE to power my Unifi AP.

## Setup

![My current home networking setup](https://res.cloudinary.com/drwjkxxud/image/upload/v1722051055/home_networking.drawio_drfiqj.png)

Currently everything is sitting on my [[hardware|server rack]] on the same network, I will need to play around with VLANs to properly segment the network and isolate guest, IoT and server traffic.