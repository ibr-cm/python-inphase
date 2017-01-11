# Program to connect inphase hardware to command and control server
---

## Install

* Link inphasebridge.py to /usr/local/bin/inphasebridge.py
* Link inphasebridge.service to ~/.local/share/systemd/user/inphasebridge.service

```
# ln -s `pwd`/inphasebridge.py /usr/local/bin/inphasebridge.py
ln -s `pwd`/inphasebridge.service  ~/.config/systemd/user/inphasebridge.service
```

This will install inphasebridge as user service so you can use systemctl to
control it:
```
systemctl --user start inphasebridge.service
systemctl --user status inphasebridge.service
systemctl --user stop inphasebridge.service
```

