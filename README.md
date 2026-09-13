# 🤖 Autonomous ROS 2 Mobile Robot (Jetson + ESP32)

This repository contains the software and hardware configuration for an autonomous mobile robot powered by an NVIDIA Jetson and an ESP32 microcontroller. The system uses ROS 2 for high-level logic, mapping, and navigation, while the ESP32 handles real-time motor control and encoder feedback via Micro-ROS.

---

## ⚙️ Hardware Architecture

### Core Components
* **High-Level Compute:** NVIDIA Jetson (running ROS 2 and Micro-ROS Agent)
* **Low-Level Controller:** ESP32 (running Micro-ROS firmware)
* **Motor Driver:** L298N
* **Actuators:** DC Motors with quadrature encoders
* **Power Source:** 11.1V LiPo/Li-ion Battery

### Power, Communication & The Common Ground
* **Power Routing:** The **11.1V battery** is wired in parallel to provide power directly to both the NVIDIA Jetson and the L298N motor driver's 12V input. The ESP32 is powered exclusively via the USB connection from the Jetson to prevent voltage conflicts.
* **The Common Ground (Critical):** The GND pins of the ESP32, the L298N driver, the encoders, and the battery **must all be wired together**. Voltage is a relative measurement; without a shared 0V reference line, the 3.3V PWM signals sent to the motor driver, or the 3.3V/5V pulses returning from the encoders, will be misread as electrical noise, resulting in erratic motor behavior or missed odometry ticks.
* **Data:** The Jetson and ESP32 communicate via a direct **Serial-over-USB** connection, guaranteeing real-time stability and zero wireless latency for high-frequency odometry and motor commands.

### ESP32 Pin Configuration
*(Update these pins based on your specific wiring before uploading the firmware)*

| Component | ESP32 Pin | Description |
| :--- | :--- | :--- |
| **L298N IN1** | `5` | Motor Left Forward |
| **L298N IN2** | `18` | Motor Left Backward |
| **L298N IN3** | `26` | Motor Right Forward |
| **L298N IN4** | `32` | Motor Right Backward |
| **Encoder Left A** | `13` | Odometry tick (Hardware Interrupt) |
| **Encoder Left B** | `4` | Odometry direction |
| **Encoder Right A** | `22` | Odometry tick (Hardware Interrupt) |
| **Encoder Right B** | `23` | Odometry direction |

---

## 💻 Software Architecture

The project is structured to maintain a clean separation between high-level computation and low-level hardware control.

### 1. The Firmware (`esp32_motor_control/`)
A PlatformIO project containing the **C++ Micro-ROS firmware**. It acts as the robot's spinal cord, subscribing to `/cmd_vel` to generate PWM signals for the L298N, and reading hardware interrupts from the encoders to publish raw tick data back to the Jetson.

### 2. The ROS 2 Workspace (`src/`)
Deployed on the NVIDIA Jetson, this workspace is divided into modular packages:

* **`turtlebot_bringup`**: The core orchestrator. It contains the main launch files that start the Micro-ROS Docker agent and load all necessary base parameters.
* **`turtlebot_hardware`**: The software bridge. It contains nodes like the `odom_calculator` which listens to the raw encoder ticks from the ESP32, applies the robot's physical kinematics (wheel radius, baseline), and translates them into standard ROS 2 `/odom` (Odometry) messages.
* **`turtlebot_description`**: The physical blueprint. It contains the URDF (Unified Robot Description Format) files, which define the robot's 3D geometry, joint limits, and sensor placements (TF transforms).
* **`turtlebot_navigation`**: The autonomous brain. Contains configurations and launch files for SLAM (Simultaneous Localization and Mapping) to build maps of unknown environments, and Nav2 to calculate paths and avoid obstacles.

---

## 🛠️ Prerequisites & Installation

### Jetson Setup (ROS 2)
1. Navigate to your ROS 2 workspace and clone the repository:
   ```bash
   git clone <YOUR_GITHUB_REPOSITORY_URL>
   ```
2. Build the ROS 2 packages:
   ```bash
   colcon build
   source install/setup.bash
   ```

### ESP32 Setup (Firmware)
1. Open the `esp32_motor_control` directory in **VS Code** with the **PlatformIO** extension installed.
2. Update the pin definitions in `src/main.cpp`.
3. Connect the ESP32 via USB, then **Build** and **Upload** the firmware.

---
## ![Picture](docs/robot1.jpg)
## ![Picture](docs/robot2.jpg)
## ![Picture](docs/robot3.jpg)
## 🚀 Running the System

Depending on your goal, you will launch different parts of the system.

### 1. Waking Up the Robot (Bringup)
**Why:** This is the foundational step. It opens the serial port, establishes the Micro-ROS connection with the ESP32, and starts calculating odometry. Without this, the robot is blind and paralyzed.

**Command:**
```bash
ros2 launch turtlebot_bringup robot.launch.py use_sim_time:=false
```
> **Note:** Wait for the `Session established` log in the terminal before proceeding.

### 2. Visualizing the Robot (Description)
**Why:** To verify that the URDF transforms are working, allowing you to see a 3D model of your robot in RViz reacting to wheel movements in real-time.

**Command:**
```bash
ros2 launch turtlebot_description display.launch.py
```

### 3. Mapping a New Room (SLAM)
**Why:** To drive the robot around manually (using teleop) while a LiDAR or depth camera scans the room, generating a 2D floor plan (`.yaml` and `.pgm` files) for future autonomous navigation.

**Command:**
```bash
ros2 launch turtlebot_navigation slam.launch.py
```

### 4. Autonomous Driving (Nav2)
**Why:** To load a previously saved map and allow the robot to calculate its own paths. You click a destination in RViz, and the robot drives there automatically while dodging dynamic obstacles.

**Command:**
```bash
ros2 launch turtlebot_navigation nav2.launch.py
```

---

## 🔋 Headless Autostart Setup (Systemd)

To achieve true autonomy without requiring an SSH connection to start the software, this project utilizes a Linux `systemd` service (`robot.service`).

**When the 11.1V battery is connected:**
1. The Jetson boots up automatically.
2. The `robot.service` triggers in the background, executing the `turtlebot_bringup` launch file.
3. The Micro-ROS agent establishes a connection with the ESP32 over USB.
4. The robot enters a standby state, fully connected to the Wi-Fi network and ready to receive `/cmd_vel` commands or Nav2 goals remotely from a base station laptop.
