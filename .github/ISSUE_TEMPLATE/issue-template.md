---
name: Issue template
about: Describe this issue here
title: ''
labels: ''
assignees: ''

---

**Describe the issue**

A clear and concise description of what the issue is.

**Expected behavior**

A clear and concise description of what you expected to happen.

**Home Assistant version**

Which Home Assistant version are you using?

And did it work on a previous version, if so what was the last working version?

**Screenshots**

If applicable, add screenshots to help explain your problem.

**Connected Drive website**

If you see any issues with the BMW integration in Home Assistant (or when directly using the library), please make sure to first login to the BMW Connected Drive website of your country and check if you can successfully login and query the car status.
- [ ] I can still successfully login to the BMW Connected Drive website and the car status is available there.
- [ ] I have Connected Drive enabled for my vehicle.

**Your config.yaml**

```yaml
bmw_connected_drive:
  name_of_car:
    username: USERNAME_BMW_CONNECTED_DRIVE
    password: PASSWORD_BMW_CONNECTED_DRIVE
    region: one of "north_america", "china" , "rest_of_world"
````

**Number of cars**

If you have more than 1 car please mention that here.
- [ ] I have 2 or more cars linked to the Connected Drive account.
- [ ] I have a Mini vehicle linked to my account.

**Output of bimmer_connected fingerprint**

If you have run the [bimmer_connected fingerprint](https://github.com/bimmerconnected/bimmer_connected#data-contributions) please share that data here

*NOTE: It might take us a while to respond on GitHub (we only maintain this in our free time), but we will respond.*
