.. _api_routes:

ApRES HTTP API Routes
=====================================

All routes are postfixed to `http://[radar IP/hostname]/api/`

System Routes
~~~~~~~~~~~~~
Related to system-level configuration and management

=========================== ===============================================
API Route                   Description
=========================== ===============================================
system/reset                Reset the ApRES
system/housekeeping/status  Get the current ApRES status
system/housekeeping/config  Download or upload a new system config.ini file
=========================== ===============================================

Radar Routes
~~~~~~~~~~~~
Related to radar-level configuration and performing bursts

=========================== ================================================
API Route                   Description
=========================== ================================================
radar/config                Get or set the current radar burst configuration
radar/trial-burst           Perform a trial burst with the current config
radar/burst                 Perform a burst with the current config
radar/results               Get results from the latest trial burst
=========================== ================================================
