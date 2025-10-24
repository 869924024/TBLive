# Taobao Device Management and Cookie Scraping System

## Project Overview

This is a comprehensive Python application designed for automated device management and data extraction from Taobao (淘宝) mobile platform. The system uses MuMu Android emulators combined with network traffic interception to generate device identification data and capture session information.

**WARNING**: This system involves automated interaction with commercial platforms and network traffic interception. Ensure compliance with applicable laws and platform terms of service before use.

## Project Structure

```
淘宝刷观看/python/
├── main.py                    # Application entry point (PyQt5 GUI)
├── ui.py                      # User interface with fluent design system
├── generate_device.py         # Core device generation and data capture
├── mumu/                     # MuMu emulator automation framework
│   ├── mumu.py               # Main API wrapper for emulator control
│   ├── config.py             # Configuration management
│   ├── control.py            # Emulator lifecycle operations
│   ├── utils.py              # Utility functions and command execution
│   ├── constant.py           # Device identification constants
│   └── api/                  # Modular API components
├── source/                   # Application resources
│   └── tm13.12.2.apk        # Taobao mobile application
└── SunnyNet/                 # Network traffic capture library
    └── SunnyNet64.dll       # Network proxy and capture engine
```

## Core Functionality

### 1. Device Generation System
The application automates the creation of Android emulators with unique device identification:

- **Emulator Creation**: Dynamically creates MuMu emulator instances
- **Configuration**: Sets mobile-optimized screen resolution (900x1600, 320 DPI)
- **App Installation**: Automatically installs Taobao mobile app (version 13.12.2)
- **Launch Automation**: Starts the application and verifies successful operation
- **Data Capture**: Extracts device identification headers via network interception

### 2. Network Traffic Interception
Uses SunnyNet proxy to capture HTTP headers containing device identifiers:

**Captured Headers:**
- `x-devid` - Device identification token
- `x-mini-wua` - Mini Program User Agent
- `x-sgext` - Signature extension
- `x-umt` - UMT authentication token
- `x-utdid` - UTDID device identifier

### 3. GUI Interface (PyQt5 + qfluentwidgets)
Modern, user-friendly interface with three main sections:

#### ① Account and Device Data Management
- Import account credentials from text files
- Generate and manage emulated device data
- Real-time device count and status monitoring

#### ② Algorithm Service Control
- Start/stop SunnyNet proxy service
- Monitor service status and error handling
- Process-specific traffic capture (MuMu emulator processes)

#### ③ Task Operations
- Execute automated tasks using generated device data
- Monitor success/failure metrics
- Real-time logging system with export capabilities

## Technical Architecture

### Key Dependencies
- **PyQt5**: GUI framework with Fluent design system
- **MuMu Emulator**: Android virtualization platform
- **SunnyNet**: Network traffic capture and proxy (DLL-based)
- **OpenCV**: Computer vision for GUI automation (optional)
- **ADB**: Android Debug Bridge integration

### API Architecture
The `mumu/` directory provides a comprehensive API for emulator control:

```python
# Example usage
from mumu.mumu import Mumu

# Create emulator instance
mumu = Mumu().select(1)  # Select emulator index 1

# Core operations
mumu.core.create(1)           # Create emulator
mumu.screen.resolution_mobile()  # Set mobile resolution
mumu.app.install('path/to/apk')  # Install app
mumu.power.start()             # Power on emulator
```

## Data Management

### Account Data (`账号.txt`)
Stores Taobao session cookies and authentication tokens:
```
thw=cn; cna=wcUWHnsnkQgCAW406Yv3eOec; tracknick=tb374144344; ...
```

### Device Data (`设备.txt`)
Captured device identification headers containing unique device identifiers used for automation and tracking.

## Configuration

### Environment Setup
1. **MuMu Emulator Installation**: 
   - Auto-detects paths: `C:\Program Files\Netease\MuMu\nx_main` or `D:\Program Files\Netease\MuMu\nx_main`
   - Requires MuMuManager.exe and adb.exe

2. **Dependencies**:
   - Install PyQt5 and qfluentwidgets: `pip install PyQt5 qfluentwidgets`
   - SunnyNet library bundled with application

3. **Application Files**:
   - Taobao APK: `source/tm13.12.2.apk`
   - Network library: `SunnyNet/SunnyNet64.dll`

## Development Workflow

### Setup and Installation
1. Ensure MuMu emulator is installed and working
2. Place Taobao APK in `source/` directory
3. Run `python main.py` to start the GUI

### Common Operations
1. **Device Generation**: Click 开始生成设备 to start device creation
2. **Service Management**: Start algorithm service to enable traffic capture
3. **Task Execution**: Use generated device data for automated operations

## Security and Legal Considerations

### Important Warnings
- **Network Interception**: This application captures network traffic requiring legal authorization
- **Platform Terms**: Automated interaction with Taobao may violate platform terms of service
- **Data Privacy**: Handle captured account and device data according to privacy regulations
- **Geographic Restrictions**: Comply with local laws regarding device emulation and data collection

### Best Practices
- Use in controlled environments for testing/analysis purposes only
- Implement proper data storage and access controls
- Monitor system performance and resource usage
- Keep dependencies and emulator software updated

## Troubleshooting

### Common Issues
1. **Emulator Creation Failed**: Check MuMu installation and permissions
2. **App Installation Timeout**: Verify APK integrity and network connectivity
3. **Service Start Failed**: Check SunnyNet DLL and administrator permissions
4. **Device Capture Failed**: Ensure proper emulator setup and app launch

### Debug Information
- Monitor console output for detailed error messages
- Check emulator process status in MuMu Manager
- Verify network connectivity and port availability
- Review log files in the GUI for operational history

## Author and Maintenance

**Primary Developer**: wlkjyy  
**Development Environment**: PyCharm  
**Platform**: Windows  
**Language**: Python 3.x

This system represents a sophisticated automation platform for device management and data extraction, requiring careful consideration of legal and ethical implications before deployment.
