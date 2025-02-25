Application Name
================
client_status


Application Version
===================
1.0


NCOS Devices Supported
======================
ALL


External Requirements
=====================


Application Purpose
===================
This application will set the device description to show a binary representation of WAN, LAN, WiFi, and IP Verify status. It will also send an alert if there are no clients connected to either LAN or WiFi.


Expected Output
===============
Sample Description:
1001
<WAN><IP Verify><LAN><WIFI>
Meaning WAN and Wi-Fi are connected, LAN has no connected clients, and at least one IP Verify test is failing. This provides a very concise and informative overview of the router's connectivity status.
Description updated every 3600 seconds
Log printed

