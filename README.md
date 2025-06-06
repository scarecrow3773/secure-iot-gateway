**Secure IoT Gateway**
=======================

This repository contains the reference implementation of a Secure IoT Gateway based on the principles of NAMUR Open Architecture (NOA) for industrial automation environments. The goal is to provide secure, modular, and protocol-independent connectivity between IT and OT systems, particularly in heterogeneous brownfield plants.

## Main Features

- **Data Aggregation**: Supports multiple industrial communication protocols (e.g., OPC UA, MODBUS/TCP)
- **Unidirectional Communication**: Strict separation of OT and IT domains in line with NOA principles
- **Verification-of-Request (VoR)**: Modular mechanism for secure validation and feedback of optimization requests
- **Authentication & Authorization**: Multi-layered security architecture, including role-based access control (RBAC)
- **Modularity**: Extendable architecture for plant-specific M+O applications and future protocol extensions

## Architecture

The system consists of several containerized components:
- Data Aggregator
- Data Provision (OPC UA Server)
- Plant-specific M+O Applications
- Verification-of-Request (VoR) Component

The architecture is designed for Docker/Compose and can be ported to hypervisor-based environments (e.g., PikeOS) in the future.


**Licensing**
------------------
Gratis or libre? ... No, gratis and libre:
This is free software (free as in speech and free as in beer) released under a MIT license. Complete licensing information is available in the [LICENSE](./LICENSE) file.
