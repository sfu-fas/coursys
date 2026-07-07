The system will use MOSS to detect similar code submissions, but we cannot distribute that code.

This directory is intended to contain the MOSS distribution, particular for Docker builds. If this directory
contains `moss.pl` and friends, it makes sense to add to `localsettings.py`:
```py
MOSS_DISTRIBUTION_PATH = './moss'
```

Our moss.pl has been modified to use more sane temp locations:
```pl
$errfile = "/tmp/mosserrors$$";
$TMP = "/tmp/mosstmp$$";
```