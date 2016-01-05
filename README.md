# `pysipp` is for people who hate SIPp
and use it for automated testing because it gets the job done...


## What is it?
A python wrapper for easily configuring and launching the infamous
[SIPp](http://sipp.sourceforge.net/). It allows for invoking multi-UA
scenarios from Python thus avoiding nightmarish shell command concoctions.


## Quick start
Say you have a couple SIPp xml scrips and a device you're looking to
test using them (eg. a B2BUA or SIP proxy). Assuming you've organized
the scripts nicely in a directory like so:

```
  test_scenario/
    cancel_before_answer_uac.xml
    uas.xml
```
and your DUT is listening on socket `10.10.8.1:5060`

```python
import pysipp
scen = pysipp.scenario(scendir='path/to/test_scenario/',
    proxy=('10.10.8.1', 5060)
)
scen()
```

If you've got multiple such scenario directories you can iterate over
them:

```python
for path, scen in pysipp.walk('path/to/scendirs/root/'):
    print("running scenario collected from {}".format(path))
    scen()
```


## Features
- (a)synchronous multi-scenario invocation
- fully plugin-able thanks to [pluggy](https://github.com/hpk42/pluggy)
- detailed console reporting

... more to come!


## Dependencies
SIPp duh. Get the latest version on
[github](http://sipp.sourceforge.net/)


## Install
from git
```
pip install pip install git+git://github.com/tgoodlet/pysipp.git
```

## Hopes and dreams
I'd love to see `pysipp` become a standard end-to-end unit testing
tool for SIPp itself (particularly if paired with `pytest`).

Other thoughts are that someone might one day write actual
Python bindings to the internals of SIPp such that a pure Python DSL
can be used instead of the silly default xml SIP-flow mini-language.
If/when that happens, pysipp can serve as the front end interface.
