#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Python Documentation Generator
Copyright (C) 2012 Matthias Bolte <matthias@tinkerforge.com>
Copyright (C) 2011 Olaf Lüke <olaf@tinkerforge.com>

generator_python_doc.py: Generator for Python documentation

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License 
as published by the Free Software Foundation; either version 2 
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the
Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""

import sys
import os
import shutil
import subprocess
import glob
import re

sys.path.append(os.path.split(os.getcwd())[0])
import common

device = None
lang = 'en'
file_path = ''

def type_to_pytype(element):
    type_dict = {
        'int8': 'int',
        'uint8': 'int',
        'int16': 'int',
        'uint16': 'int',
        'int32': 'int',
        'uint32': 'int',
        'int64': 'int',
        'uint64': 'int',
        'bool': 'bool',
        'char': 'chr',
        'string': 'str',
        'float': 'float'
    }

    t = type_dict[element[1]]
    
    if element[2] == 1 or t == 'str':
        return t

    return '[' + ', '.join([t]*element[2]) + ']'

def fix_links(text):
    parameter = {
    'en': 'parameter',
    'de': 'Parameter'
    }
    parameters = {
    'en': 'parameters',
    'de': 'Parameter'
    }

    cls = device.get_camel_case_name()
    for packet in device.get_packets():
        name_false = ':func:`{0}`'.format(packet.get_camel_case_name())
        if packet.get_type() == 'callback':
            name_upper = packet.get_upper_case_name()
            name_right = ':py:attr:`{0}.CALLBACK_{1}`'.format(cls, name_upper)
        else:
            name_right = ':py:func:`{0}.{1}`'.format(cls, packet.get_underscore_name())
        text = text.replace(name_false, name_right)

    text = text.replace(":word:`parameter`", parameter[lang])
    text = text.replace(":word:`parameters`", parameters[lang])

    return text

def make_examples():
    def title_from_file(f):
        f = f.replace('example_', '')
        f = f.replace('.py', '')
        s = ''
        for l in f.split('_'):
            s += l[0].upper() + l[1:] + ' '
        return s[:-1]

    return common.make_rst_examples(title_from_file, device, file_path,
                                    'python', 'example_', '.py', 'Python')

def make_parameter_list(packet):
    params = []
    for element in packet.get_elements('in'):
        params.append(element[0])
    return ", ".join(params)

def make_parameter_desc(packet, io):
    desc = '\n'
    param = ' :param {0}: {1}\n'
    for element in packet.get_elements(io):
        t = type_to_pytype(element)
        desc += param.format(element[0], t)

    return desc

def make_return_desc(packet):
    ret = ' :rtype: {0}\n'
    ret_list = []
    for element in packet.get_elements('out'):
        ret_list.append(type_to_pytype(element))
    if len(ret_list) == 0:
        return ret.format(None)
    elif len(ret_list) == 1:
        return ret.format(ret_list[0])
    
    return ret.format('(' + ', '.join(ret_list) + ')')

def make_methods(typ):
    version_method = {
    'en': """
.. py:function:: {0}.get_version()

 :rtype: (str, [int, int, int], [int, int, int])

 Returns the name (including the hardware version), the firmware version 
 and the binding version of the device. The firmware and binding versions are
 given in arrays of size 3 with the syntax [major, minor, revision].
""",
    'de': """
.. py:function:: {0}.get_version()

 :rtype: (str, [int, int, int], [int, int, int])
 
 Gibt den Namen (inklusive Hardwareversion), die Firmwareversion 
 und die Bindingsversion des Gerätes zurück. Die Firmware- und Bindingsversionen werden
 als Array der Größe 3 mit der Syntax [Major, Minor, Revision] zurückgegeben.
"""
    }

    methods = ''
    func_start = '.. py:function:: '
    cls = device.get_camel_case_name()
    for packet in device.get_packets('function'):
        if packet.get_doc()[0] != typ:
            continue
        name = packet.get_underscore_name()
        params = make_parameter_list(packet)
        pd = make_parameter_desc(packet, 'in')
        r = make_return_desc(packet)
        d = fix_links(common.shift_right(packet.get_doc()[1][lang], 1))
        desc = '{0}{1}{2}'.format(pd, r, d)
        func = '{0}{1}.{2}({3})\n{4}'.format(func_start, 
                                             cls, 
                                             name, 
                                             params, 
                                             desc)
        methods += func + '\n'

    if typ == 'af':
        methods += version_method[lang].format(cls)

    return methods 

def make_callbacks():
    cbs = ''
    func_start = '.. py:attribute:: '
    cls = device.get_camel_case_name()
    for packet in device.get_packets('callback'):
        param_desc = make_parameter_desc(packet, 'out')
        desc = fix_links(common.shift_right(packet.get_doc()[1][lang], 1))

        func = '{0}{1}.CALLBACK_{2}\n{3}\n{4}'.format(func_start,
                                                      cls,
                                                      packet.get_upper_case_name(),
                                                      param_desc,
                                                      desc)
        cbs += func + '\n'

    return cbs

def make_api():
    create_str = {
    'en': """
.. py:function:: {1}(uid)

 Creates an object with the unique device ID *uid*:

 .. code-block:: python

    {0} = {1}("YOUR_DEVICE_UID")

 This object can then be added to the IP connection (see examples 
 :ref:`above <{0}_{2}_python_examples>`).
""",
    'de': """
.. py:function:: {1}(uid)

 Erzeugt ein Objekt mit der eindeutigen Geräte ID *uid*:

 .. code-block:: python

    {0} = {1}("YOUR_DEVICE_UID")

 Dieses Objekt kann danach der IP Connection hinzugefügt werden (siehe Beispiele
 :ref:`oben <{0}_{2}_python_examples>`).
"""
    }

    register_str = {
    'en': """
.. py:function:: {1}.register_callback(id, callback)

 :param id: int
 :param callback: callable
 :rtype: None

 Registers a callback with ID *id* to the function *callback*. The available
 IDs with corresponding function signatures are listed 
 :ref:`below <{0}_{2}_python_callbacks>`.
""",
    'de': """
.. py:function:: {1}.register_callback(id, callback)

 :param id: int
 :param callback: callable
 :rtype: None

 Registriert einen Callback mit der ID *id* mit der Funktion *callback*. Die verfügbaren
 IDs mit den zugehörigen Funktionssignaturen sind :ref:`unten <{0}_{2}_python_callbacks>`
 zu finden.
"""
    }

    c_str = {
    'en': """
.. _{1}_{2}_python_callbacks:

Callbacks
^^^^^^^^^

*Callbacks* can be registered with *callback IDs* to receive
time critical or recurring data from the device. The registration is done
with the :py:func:`register_callback <{3}.register_callback>` function of
the device object. The first parameter is the callback ID and the second
parameter the callback function:

.. code-block:: python

    def my_callback(param):
        print(param)

    {1}.register_callback({3}.CALLBACK_EXAMPLE, my_callback)

The available constants with inherent number and type of parameters are 
described below.

.. note::
 Using callbacks for recurring events is *always* preferred
 compared to using getters. It will use less USB bandwidth and the latency
 will be a lot better, since there is no round trip time.

{0}
""",
    'de': """
.. _{1}_{2}_python_callbacks:

Callbacks
^^^^^^^^^

*Callbacks* können mit *callback IDs* registriert werden um zeitkritische
oder wiederkehrende Daten vom Gerät zu erhalten. Die Registrierung kann
mit der Funktion :py:func:`register_callback <{3}.register_callback>` des 
Geräte Objektes durchgeführt werden. Der erste Parameter ist der Callback ID
und der zweite Parameter die Callbackfunktion:

.. code-block:: python

    def my_callback(param):
        print(param)

    {1}.register_callback({3}.CALLBACK_EXAMPLE, my_callback)

Die verfügbaren Konstanten mit der dazugehörigen Parameteranzahl und -typen werden
weiter unten beschrieben.

.. note::
 Callbacks für wiederkehrende Ereignisse zu verwenden ist 
 *immer* zu bevorzugen gegenüber der Verwendung von Abfragen.
 Es wird weniger USB-Bandbreite benutzt und die Latenz ist
 erheblich geringer, da es keine Paketumlaufzeit gibt.

{0}
"""
    }

    api = {
    'en': """
{0}
API
---

All methods listed below are thread-safe.

{1}

{2}
""",
    'de': """
{0}
API
---

Alle folgend aufgelisteten Funktionen sind Thread-sicher.

{1}

{2}
"""
    }

    cre = create_str[lang].format(device.get_underscore_name(),
                            device.get_camel_case_name(),
                            device.get_category().lower())
    reg = register_str[lang].format(device.get_underscore_name(),
                              device.get_camel_case_name(),
                              device.get_category().lower())

    bf = make_methods('bf')
    af = make_methods('af')
    ccf = make_methods('ccf')
    c = make_callbacks()
    api_str = ''
    if bf:
        api_str += common.bf_str[lang].format(cre, bf)
    if af:
        api_str += common.af_str[lang].format(af)
    if c:
        api_str += common.ccf_str[lang].format(reg, ccf)
        api_str += c_str[lang].format(c, device.get_underscore_name(),
                                      device.get_category().lower(),
                                      device.get_camel_case_name())

    ref = '.. _{0}_{1}_python_api:\n'.format(device.get_underscore_name(),
                                             device.get_category().lower())

    api_desc = ''
    try:
        api_desc = device.com['api'][lang]
    except KeyError:
        pass

    return api[lang].format(ref, api_desc, api_str)
       
def copy_examples_for_zip():
    examples = common.find_examples(device, file_path, 'python', 'example_', '.py')
    dest = os.path.join('/tmp/generator/egg/examples/', 
                        device.get_category().lower(),
                        device.get_underscore_name())

    if not os.path.exists(dest):
        os.makedirs(dest)

    for example in examples:
        shutil.copy(example[1], dest)
  
def make_files(com_new, directory):
    global device
    device = common.Device(com_new)
    file_name = '{0}_{1}_Python'.format(device.get_camel_case_name(), device.get_category())
    title = {
    'en': 'Python bindings',
    'de': 'Python Bindings'
    }

    directory += '/doc'
    if not os.path.exists(directory):
        os.makedirs(directory)

    f = file('{0}/{1}.rst'.format(directory, file_name), "w")
    f.write(common.make_rst_header(device, 'python', 'Python'))
    f.write(common.make_rst_summary(device, title[lang]))
    f.write(make_examples())
    f.write(make_api())

    copy_examples_for_zip()

def generate(path):
    global file_path
    file_path = path
    path_list = path.split('/')
    path_list[-1] = 'configs'
    path_config = '/'.join(path_list)
    sys.path.append(path_config)
    configs = os.listdir(path_config)

    # Make temporary generator directory
    if os.path.exists('/tmp/generator'):
        shutil.rmtree('/tmp/generator/')
    os.makedirs('/tmp/generator/egg/source/tinkerforge')
    os.chdir('/tmp/generator')

    # Make bindings
    for config in configs:
        if config.endswith('_config.py'):
            module = __import__(config[:-3])
            print(" * {0}".format(config[:-10]))            
            make_files(module.com, path)

    # Copy bindings and readme
    for filename in glob.glob(path + '/bindings/*.py'):
        shutil.copy(filename, '/tmp/generator/egg/source/tinkerforge')

    shutil.copy(path + '/ip_connection.py', '/tmp/generator/egg/source/tinkerforge')
    shutil.copy(path + '/changelog.txt', '/tmp/generator/egg')
    shutil.copy(path + '/readme.txt', '/tmp/generator/egg')

    # Write setup.py
    version = common.get_changelog_version(path)
    file('/tmp/generator/egg/source/setup.py', 'wb').write("""
#!/usr/bin/env python

from setuptools import setup

setup(name='tinkerforge',
      version='{0}.{1}.{2}',
      description='TCP/IP based library for Bricks and Bricklets',
      author='Tinkerforge GmbH',
      author_email='olaf@tinkerforge.com',
      url='http://www.tinkerforge.com',
      packages=['tinkerforge'])
""".format(*version))

    # Make egg
    os.chdir('/tmp/generator/egg/source')
    args = ['/usr/bin/python',
            'setup.py',
            'bdist_egg']
    subprocess.call(args)

    # Remove build stuff
    shutil.rmtree('/tmp/generator/egg/source/build')
    shutil.rmtree('/tmp/generator/egg/source/tinkerforge.egg-info')
    shutil.copy('/tmp/generator/egg/source/dist/' + 
                os.listdir('/tmp/generator/egg/source/dist')[0], 
                '/tmp/generator/egg/tinkerforge.egg')
    shutil.rmtree('/tmp/generator/egg/source/dist')

    # Make __init__.py
    f = open('/tmp/generator/egg/source/tinkerforge/__init__.py', 'w')
    f.write(' ')
    f.close()

    # Make zip
    common.make_zip('python', '/tmp/generator/egg', path, version)

if __name__ == "__main__":
    generate(os.getcwd())
