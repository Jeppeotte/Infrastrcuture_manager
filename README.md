# Infrastructure Manager

This repository contains the **Infrastructure Manager** software, developed as part of a Master's Thesis from Aalborg University.

## Overview

The Infrastructure Manager runs on the backend server and provides full infrastructure management and configuration for your edge gateways.

This software includes:

- Databases and scripts for data insertion
- MQTT broker for message communication
- Grafana for data visualization
- A web-based **UI to configure gateways**, allowing you to select which gateways connect to which devices in your process

> **Note:** This software does **not** connect directly to PLCs or sensors. It manages and configures gateways that have been set up using the software from [Repository 1](https://github.com/Jeppeotte/PI_Edgegateway/tree/master).

Additional guides for establishing connections between:

- Gateways and the backend  
- Gateways and various devices  

are provided in a separate folder within this repository.

---

## Supported Hardware and Operating Systems

- **Architecture:** amd64 only  
- **Tested hardware:** Intel NUC with 32 GB RAM  
  *(Model details will be added soon)*  
- **Tested operating systems:**  
  - Ubuntu 24.04.2 LTS  
  - Ubuntu 25.04  

The software should run on other amd64 Linux systems with sufficient resources, but only Ubuntu versions above have been explicitly tested.

---

## Setup Guide

### 1. Prepare Your Device

Make sure your device runs a supported Ubuntu version (24.04.2 LTS or 25.04) with amd64 architecture and has Docker installed.

---

### 2. Set a Static IP Address for Communication

For communication with gateways and devices, set a static IP address as follows.

To make the IP address permanent, edit the `dhcpcd.conf` file:

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:

```conf
interface eth0
static ip_address=172.20.1.152/24
```

* Replace `172.20.1.152` with your desired static IP.

Save and exit (`Ctrl+X`, then `Y`, then `Enter`).

Reboot for changes to take effect:

```bash
sudo reboot
```

Verify the static IP after reboot:

```bash
ip a show eth0
```

---

### 3. Configure Docker Compose

Create a folder where the software files will be stored, and inside that folder create a file named `docker-compose.yaml`.

Copy the Docker Compose file from this repository into your `docker-compose.yaml`.

Modify the following to suit your system:

- In the `volumes` section, update the path mapping to the absolute path of your folder:

```yaml
  volumes:
    - /absolute/path/to/your/folder:/mounted_dir:rw
    - /var/run/docker.sock:/var/run/docker.sock:rw
```

* Set environment variables for system platform and architecture:

  ```yaml
  environment:
    HOST_PLATFORM: linux
    HOST_ARCH: amd64
  ```

* Add or adjust other environment variables as needed (refer to the Docker Compose file comments).

---

### 4. Launch the Infrastructure Manager

Open a terminal, navigate to the folder with `docker-compose.yaml`, and run:

```bash
sudo docker compose up -d
```

To verify containers are running:

```bash
sudo docker ps
```
---

## Additional Notes

* The Infrastructure Manager manages backend services and provides a UI for gateway configuration.
* Network accessibility between the backend server and gateways is essential.
* See the `guides` folder for detailed instructions on connecting gateways to this backend and to devices.

