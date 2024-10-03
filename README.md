# Zketech Mono-Channel Battery Testers Replacement Program

## Introduction

The original Zketech program has the following drawbacks
- It is to be downloaded on a Chinese only website
- It is available only on Windows
- It is available only in Chinese and English
- It has several bugs (multisteps programs, calibration, etc.)

Moreover, Zketech devices are shipped with Chinese only manuals.

This depot is intended to provide an alternative cross-platform interface.

## Control module

The 'zketech.py' module provides the main control functions of the device.

## Interfaces

### Textual

The 'cmd_control.py' module provides a simple text interface.

### Graphical

No graphical interface is provided for now.

## Tanslated manuals

Partially translated manuals are provided in the 'user_manuals' folder

## Next developpement stage

The next developpement stages shall be:
- Building a graphical interface with support for local languages and multiple steps tests described in text files
- Fixing upper boundaries checks when launching tests
- Finding the exchange frames when performing a calibration
