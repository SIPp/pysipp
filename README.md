[![Build Status](https://travis-ci.org/SIPp/pysipp.svg?branch=master)](https://travis-ci.org/SIPp/pysipp)
# `pysipp` is for people who hate SIPp
but (want to) use it for automated testing because it gets the job done...


## What is it?
Python configuring and launching the infamous
[SIPp](http://sipp.sourceforge.net/) using an api inspired by
[requests](http://docs.python-requests.org/)

## It definitely lets you

- Launch multi-UA scenarios (aka SIPp subprocesses) sanely
  * avoids nightmarish shell command concoctions from multiple terminals
  * allows for complex functional or end-to-end SIP testing
- Reuse your existing SIPp XML scripts
- Integrate nicely with [pytest](http://pytest.org/)


## It doesn't try to

- Auto-generate SIPp XML scripts like [sippy_cup](https://github.com/mojolingo/sippy_cup)
  * `pysipp` in no way tries to work around the problem of SIPp's awful
    XML control language; your current scenario scripts are compatible!


## Basic Usage
Launching the default UAC scenario is a short line:

```python
import pysipp
pysipp.client(destaddr=('10.10.8.88', 5060))()
```

Manually running the default `uac` --calls--> `uas` scenario is also simple:

```python
uas = pysipp.server(srcaddr=('10.10.8.88', 5060))
uac = pysipp.client(destaddr=uas.srcaddr)
# run server async
uas(block=False)  # returns a `pysipp.launch.PopenRunner` instance by default
uac()  # run client synchronously
```

## Authentication
When using the `[authentication]` [sipp keyword](https://sipp.readthedocs.io/en/latest/scenarios/keywords.html#authentication)
in scenarios, providing the credentials can be done with the
`auth_username` and `auth_password` arguments, for example:

```python
pysipp.client(auth_username='sipp', auth_password='sipp-pass')
```

## Multiple Agents
For multi-UA orchestrations we can use a `pysipp.scenario`.
The scenario from above is the default agent configuration:

```python
scen = pysipp.scenario()
scen()  # run uac and uas synchronously to completion
```

Say you have a couple SIPp xml scrips and a device you're looking to
test using them (eg. a B2BUA or SIP proxy). Assuming you've organized
the scripts nicely in a directory like so:

```
test_scenario/
  uac.xml
  referer_uas.xml
  referee_uas.xml
```

If you've configured your DUT to listen for for SIP on `10.10.8.1:5060`
and route traffic to the destination specified in the SIP `Request-URI` header
and your local ip address is `10.10.8.8`:

```python
scen = pysipp.scenario(dirpath='path/to/test_scenario/',
                       proxyaddr=('10.10.8.1', 5060))

# run all agents in sequence starting with servers
scen()
```

**pysipp** by default uses `-screen_file` SIPp argument to redirect output,
 but this argument is only available in SIPp version >= [3.5.0](https://sourceforge.net/p/sipp/mailman/message/34041962/),
 for lower versions to run properly, this argument must be
  disable setting `enable_screen_file` to `False`:
 
```python
scen = pysipp.scenario(enable_screen_file=False)
```

If you've got multiple such scenario directories you can iterate over
them:

```python
for path, scen in pysipp.walk('path/to/scendirs/root/'):
    print("Running scenario collected from {}".format(path))
    scen()
```

## Async Scenario Launching
You can also launch multiple multi-UA scenarios concurrently using
non-blocking mode:

```python
scens = []
for path, scen in pysipp.walk('path/to/scendirs/root/', proxyaddr=('10.10.8.1', 5060)):
    print("Running scenario collected from {}".format(path))
    scen(block=False)
    scens.append(scen)

# All scenarios should now be running concurrently so we can continue
# program execution...
print("Continuing program execution...")

# Wait to collect all the results
print("Finalizing all scenarios and collecting results")
for scen in scens:
  scen.finalize()
```

`scen.finalize()` actually calls a special cleanup function defined in the
[`pysipp_run_protocol`](https://github.com/SIPp/pysipp/blob/master/pysipp/__init__.py#L207)
hook which invokes the internal reporting functions and returns a `dict` of cmd -> process
items.

## API
To see the mapping of SIPp command line args to `pysipp.agent.UserAgent`
attributes, take a look at `pysipp.command.sipp_spec`.
This should give you an idea of what can be set on each agent.


## Features
- (a)synchronous multi-scenario invocation
- fully plugin-able thanks to [pluggy](https://github.com/hpk42/pluggy)
- detailed console reporting

... more to come!


## Dependencies
SIPp duh...Get the latest version on [github](https://github.com/SIPp/sipp)


## Install
from git
```
pip install git+git://github.com/SIPp/pysipp.git
```


## Hopes and dreams
I'd love to see `pysipp` become a standard end-to-end unit testing
tool for SIPp itself (particularly if paired with `pytest`).

Other thoughts are that someone might one day write actual
Python bindings to the internals of SIPp such that a pure Python DSL
can be used instead of the silly default xml SIP-flow mini-language.
If/when that happens, pysipp can serve as a front end interface.


## Advanced Usage
`pysipp` comes packed with some nifty features for customizing
SIPp default command configuration and launching as well as detailed
console reporting. There is even support for remote execution of SIPp
over the network using [rpyc](https://rpyc.readthedocs.org/en/latest/)

### Enable detailed console reporting
```python
pysipp.utils.log_to_stderr("DEBUG")
```

### Applying default settings
For now see [#4](https://github.com/SIPp/pysipp/issues/4)

## More to come?
- document attributes / flags
- writing plugins
- using a `pysipp_conf.py`
- remote execution
- async mult-scenario load testing
