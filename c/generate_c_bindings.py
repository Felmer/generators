#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C/C++ Bindings Generator
Copyright (C) 2012 Matthias Bolte <matthias@tinkerforge.com>
Copyright (C) 2011 Olaf Lüke <olaf@tinkerforge.com>

generator_c_bindings.py: Generator for C/C++ bindings

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

import datetime
import sys
import os

sys.path.append(os.path.split(os.getcwd())[0])
import common

device = None
lang = 'en'

def fix_links(text):
    link = '{{@link {0}_{1}}}'
    link_c = '{{@link {0}_CALLBACK_{1}}}'

    # handle tables
    lines = text.split('\n')
    replaced_lines = []
    in_table_head = False
    in_table_body = False

    for line in lines:
        if line.strip() == '.. csv-table::':
            in_table_head = True
            replaced_lines.append('\\verbatim')
        elif line.strip().startswith(':header: ') and in_table_head:
            replaced_lines.append(line[len(':header: '):])
        elif line.strip().startswith(':widths:') and in_table_head:
            pass
        elif len(line.strip()) == 0 and in_table_head:
            in_table_head = False
            in_table_body = True

            replaced_lines.append('')
        elif len(line.strip()) == 0 and in_table_body:
            in_table_body = False

            replaced_lines.append('\\endverbatim')
            replaced_lines.append('')
        else:
            replaced_lines.append(line)

    text = '\n'.join(replaced_lines)

    for packet in device.get_packets():
        name_false = ':func:`{0}`'.format(packet.get_camel_case_name())
        if packet.get_type() == 'callback':
            name = packet.get_upper_case_name()
            name_right = link_c.format(device.get_upper_case_name(), name)
        else:
            name = packet.get_underscore_name()
            name_right = link.format(device.get_underscore_name(), name)

        text = text.replace(name_false, name_right)

    text = text.replace(":word:`parameter`", "parameter")
    text = text.replace(":word:`parameters`", "parameters")
    text = text.replace('.. note::', '\\note')
    text = text.replace('.. warning::', '\\warning')

    return text

def make_parameter_list(packet):
    param = ''
    for element in packet.get_elements():
        c_type = get_c_type(element[1])
        name = element[0]
        pointer = ''
        arr = ''
        if element[3] == 'out':
            pointer = '*'
            name = "ret_{0}".format(name)
        if element[2] > 1:
            arr = '[{0}]'.format(element[2])
            pointer = ''
       
        param += ', {0} {1}{2}{3}'.format(c_type, pointer, name, arr)
    return param

def make_short_form(name):
    short = ''
    for x in name.split('_'):
        short += x[0].lower()

    return short

def get_c_type(py_type):
    if py_type == 'string':
        return 'char'
    if py_type in ( 'int8',  'int16',  'int32' , 'int64', \
                   'uint8', 'uint16', 'uint32', 'uint64'):
        return "{0}_t".format(py_type)
    return py_type

def make_include_c():
    include = """{0}
#include "{1}_{2}.h"

#include <string.h>

"""
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    return include.format(common.gen_text_star.format(date),
                          device.get_category().lower(),
                          device.get_underscore_name())

def make_function_id_defines():
    define_temp = '#define FUNCTION_{0} {1}\n'

    defines = ''
    for packet in device.get_packets('function'):
        defines += define_temp.format(packet.get_upper_case_name(), packet.get_function_id())

    return defines

def make_callback_defines():
    define_temp = """
/**
 * \ingroup {5}{4}
 *
 * {3}
 */
#define {0}_CALLBACK_{1} {2}
"""

    defines = ''
    for packet in device.get_packets('callback'):
        doc = '\n * '.join(fix_links(packet.get_doc()[1][lang]).strip().split('\n'))
        defines += define_temp.format(device.get_upper_case_name(),
                                      packet.get_upper_case_name(),
                                      packet.get_function_id(),
                                      doc,
                                      device.get_camel_case_name(),
                                      device.get_category())

    return defines

def make_structs():
    structs = """
#if defined _MSC_VER || defined __BORLANDC__
\t#pragma pack(push)
\t#pragma pack(1)
\t#define ATTRIBUTE_PACKED
#elif defined __GNUC__
\t#define ATTRIBUTE_PACKED __attribute__((packed))
#else
\t#error unknown compiler, do not know how to enable struct packing
#endif
"""

    struct_temp = """
typedef struct {{
\tuint8_t stack_id;
\tuint8_t function_id;
\tuint16_t length;
{0}}} ATTRIBUTE_PACKED {1}{2}_;
"""

    for packet in device.get_packets():
        if packet.get_type() == 'callback':
            cb = "Callback"
            struct_body = ''
            for element in packet.get_elements():
                c_type = get_c_type(element[1])
                if element[2] > 1:
                    struct_body += '\t{0} {1}[{2}];\n'.format(c_type,
                                                              element[0],
                                                              element[2]);
                else:
                    struct_body += '\t{0} {1};\n'.format(c_type, element[0])

            structs += struct_temp.format(struct_body, packet.get_camel_case_name(), cb)
            continue

        struct_body = ''
        for element in packet.get_elements('in'):
            c_type = get_c_type(element[1])
            if element[2] > 1:
                struct_body += '\t{0} {1}[{2}];\n'.format(c_type,
                                                          element[0],
                                                          element[2]);
            else:
                struct_body += '\t{0} {1};\n'.format(c_type, element[0])

        structs += struct_temp.format(struct_body, packet.get_camel_case_name(), '')

        if len(packet.get_elements('out')) == 0:
            continue

        struct_body = ''
        for element in packet.get_elements('out'):
            c_type = get_c_type(element[1])
            if element[2] > 1:
                struct_body += '\t{0} {1}[{2}];\n'.format(c_type,
                                                          element[0],
                                                          element[2]);
            else:
                struct_body += '\t{0} {1};\n'.format(c_type, element[0])

        structs += struct_temp.format(struct_body, packet.get_camel_case_name(), 'Return')

    structs += """
#if defined _MSC_VER || defined __BORLANDC__
\t#pragma pack(pop)
#endif
#undef ATTRIBUTE_PACKED
"""    
    return structs

def make_create_func():
    func = """
void {0}_create({1} *{0}, const char *uid) {{
\tipcon_device_create({0}, uid);

\t{0}->expected_name = "{6} {7}";

\t{0}->binding_version[0] = {3};
\t{0}->binding_version[1] = {4};
\t{0}->binding_version[2] = {5};
{2}\n}}
"""

    cb_temp = """
\t{0}->callback_wrappers[{3}_CALLBACK_{1}] = {0}_callback_wrapper_{2};"""

    cbs = ''
    dev_name = device.get_underscore_name()
    for packet in device.get_packets('callback'):
        type_name = packet.get_underscore_name()
        cbs += cb_temp.format(dev_name, type_name.upper(), type_name, dev_name.upper())
    
    v = device.get_version()
    return func.format(dev_name, device.get_camel_case_name(), cbs, v[0], v[1], v[2],
                       device.get_display_name(), device.get_category())

def make_method_funcs():
    def make_struct_list(packet):
        struct_list = ''
        for element in packet.get_elements('in'):
            sf = make_short_form(packet.get_underscore_name())
            if element[1] == 'string':
                temp = '\n\tstrncpy({0}.{1}, {1}, {2});\n'
                struct_list += temp.format(sf, element[0], element[2])
            elif element[2] > 1:
                if common.get_type_size(element[1]) > 1:
                    struct_list += '\n\tfor (int i = 0; i < {3}; i++) {0}.{1}[i] = ipcon_leconvert_{2}_to({1}[i]);' \
                                   .format(sf, element[0], element[1], element[2])
                else:
                    temp = '\n\tmemcpy({0}.{1}, {1}, {2}*sizeof({3}));'
                    struct_list += temp.format(sf,
                                               element[0],
                                               element[2],
                                               get_c_type(element[1]))
            elif common.get_type_size(element[1]) > 1:
                struct_list += '\n\t{0}.{1} = ipcon_leconvert_{2}_to({1});'.format(sf, element[0], element[1])
            else:
                struct_list += '\n\t{0}.{1} = {1};'.format(sf, element[0])
        return struct_list

    def make_return_list(packet):
        return_list = ''
        for element in packet.get_elements('out'):
            sf = make_short_form(packet.get_underscore_name())
            if element[1] == 'string':
                temp = '\tstrcpy(ret_{0}, {1}r->{0});\n'
                return_list += temp.format(element[0], sf)
            elif element[2] > 1:
                if common.get_type_size(element[1]) > 1:
                    return_list += '\tfor (int i = 0; i < {3}; i++) ret_{0}[i] = ipcon_leconvert_{2}_from({1}r->{0}[i]);\n' \
                                   .format(element[0], sf, element[1], element[2])
                else:
                    temp = '\tmemcpy(ret_{0}, {1}r->{0}, {2}*sizeof({3}));\n'
                    return_list += temp.format(element[0],
                                               sf,
                                               element[2],
                                               get_c_type(element[1]))
            elif common.get_type_size(element[1]) > 1:
                return_list += '\t*ret_{0} = ipcon_leconvert_{2}_from({1}r->{0});\n'.format(element[0], sf, element[1])
            else:
                return_list += '\t*ret_{0} = {1}r->{0};\n'.format(element[0], sf)
        return return_list

    func_version = """
int {0}_get_version({1} *{0}, char ret_name[40], uint8_t ret_firmware_version[3], uint8_t ret_binding_version[3]) {{
\tstrncpy(ret_name, {0}->name, 40);

\tret_firmware_version[0] = {0}->firmware_version[0];
\tret_firmware_version[1] = {0}->firmware_version[1];
\tret_firmware_version[2] = {0}->firmware_version[2];

\tret_binding_version[0] = {0}->binding_version[0];
\tret_binding_version[1] = {0}->binding_version[1];
\tret_binding_version[2] = {0}->binding_version[2];

\treturn E_OK;
}}
"""

    func = """
int {0}_{1}({2} *{0}{3}) {{
\tif({0}->ipcon == NULL) {{
\t\treturn E_NOT_ADDED;
\t}}

\tipcon_mutex_lock(&{0}->write_mutex);

{9}\t{5}_ {6};
\t{6}.stack_id = {0}->stack_id;
\t{6}.function_id = {4};
\t{6}.length = ipcon_leconvert_uint16_to(sizeof({5}_));{7}

\tipcon_device_write({0}, (char *)&{6}, sizeof({5}_));

{10}{8}\tipcon_mutex_unlock(&{0}->write_mutex);

\treturn E_OK;
}}
"""

    func_ret = """\t{0}Return_ *{1}r = ({0}Return_ *){2}->response.buffer;
{3}
"""

    sizeof_ret = """\t{0}->response.function_id = {1};
\t{0}->response.length = sizeof({2}Return_);
"""

    expect_response = """\tif(ipcon_device_expect_response({0}) != 0) {{
\t\tipcon_mutex_unlock(&{0}->write_mutex);
\t\treturn E_TIMEOUT;
\t}}

"""

    a = device.get_underscore_name()
    c = device.get_camel_case_name()

    funcs = ''
    for packet in device.get_packets('function'):
        b = packet.get_underscore_name()
        d = make_parameter_list(packet)
        e = 'FUNCTION_{0}'.format(packet.get_upper_case_name())
        f = packet.get_camel_case_name()
        g = make_short_form(b)
        h = make_struct_list(packet)
        if len(packet.get_elements('out')) > 0:
            i = func_ret.format(f, g, a, make_return_list(packet))
            j = sizeof_ret.format(a, e, f)
            k = expect_response.format(a)
        else:
            i = ''
            j = ''
            k = ''

        funcs += func.format(a, b, c, d, e, f, g, h, i, j, k)

    return funcs + func_version.format(a, c)

def make_register_callback_func():
    func = """
void {0}_register_callback({1} *{0}, uint8_t id, void *callback) {{
\t{0}->registered_callbacks[id] = callback;
}}
"""
    return func.format(device.get_underscore_name(), device.get_camel_case_name())

def make_callback_wrapper_funcs():
    func = """
static int {0}_callback_wrapper_{1}({2} *{0}, const unsigned char *buffer) {{
\t{3}Callback_ *{4}c = ({3}Callback_ *)buffer;
{6}
\t(({1}_func_t){0}->registered_callbacks[{4}c->function_id])({5});
\treturn sizeof({3}Callback_);
}}
"""

    funcs = ''
    for packet in device.get_packets('callback'):
        a = device.get_underscore_name()
        b = packet.get_underscore_name()
        c = device.get_camel_case_name()
        d = packet.get_camel_case_name()
        e = make_short_form(b)
        f_list = []
        for element in packet.get_elements():
            f_list.append("{0}c->{1}".format(e, element[0]))
        f = ', '.join(f_list)
        endian_list = []
        for element in packet.get_elements():
            if common.get_type_size(element[1]) > 1:
                if element[2] > 1:
                    endian_list.append('\tfor (int i = 0; i < {3}; i++) {0}c->{1}[i] = ipcon_leconvert_{2}_from({0}c->{1}[i]);' \
                                      .format(e, element[0], element[1], element[2]))
                else:
                    endian_list.append('\t{0}c->{1} = ipcon_leconvert_{2}_from({0}c->{1});'.format(e, element[0], element[1]))
        endian = '\n'.join(endian_list)
        if len(endian) > 0:
            endian += ''

        funcs += func.format(a, b, c, d, e, f, endian)

    return funcs

def make_include_h():
    include = """{0}
#ifndef {1}_{2}_H
#define {1}_{2}_H

#include "ip_connection.h"

/**
 * \defgroup {4}{3} {3} {4}
 */

/**
 * \ingroup {4}{3}
 *
 * {5}
 */
typedef Device {3};
"""

    date = datetime.datetime.now().strftime("%Y-%m-%d")
    upper_type = device.get_category().upper()
    upper_name = device.get_upper_case_name()

    return include.format(common.gen_text_star.format(date),
                          upper_type, 
                          upper_name, 
                          device.get_camel_case_name(),
                          device.get_category(),
                          device.get_description())

def make_end_h():
    return "\n#endif\n"

def make_typedefs():
    typedef = """
typedef void (*{0}_func_t)({1});
"""

    typedefs = '\n'
    for packet in device.get_packets('callback'):
        name = packet.get_underscore_name()
        c_type_list = []
        for element in packet.get_elements():
            c_type_list.append(get_c_type(element[1]))

        typedefs += typedef.format(name, ', '.join(c_type_list))

    return typedefs

def make_create_declaration():
    create = """
/**
 * \ingroup {2}{1}
 *
 * Creates an object with the unique device ID \c uid. This object can then be
 * added to the IP connection.
 */
void {0}_create({1} *{0}, const char *uid);
"""
    return create.format(device.get_underscore_name(),
                         device.get_camel_case_name(),
                         device.get_category())

def make_method_declarations():
    func_version = """
/**
 * \ingroup {2}{1}
 *
 * Returns the name (including the hardware version), the firmware version
 * and the binding version of the device. The firmware and binding versions are
 * given in arrays of size 3 with the syntax [major, minor, revision].
 */
int {0}_get_version({1} *{0}, char ret_name[40], uint8_t ret_firmware_version[3], uint8_t ret_binding_version[3]);
"""
    func = """
/**
 * \ingroup {5}{2}
 *
 * {4}
 */
int {0}_{1}({2} *{0}{3});
"""

    a = device.get_underscore_name()
    c = device.get_camel_case_name()

    funcs = ''
    for packet in device.get_packets('function'):
        b = packet.get_underscore_name()
        d = make_parameter_list(packet)
        doc = '\n * '.join(fix_links(packet.get_doc()[1][lang]).strip().split('\n'))

        funcs += func.format(a, b, c, d, doc, device.get_category())

    return funcs + func_version.format(a, c, device.get_category())

def make_register_callback_declaration():
    if device.get_callback_count() == 0:
        return '\n'

    func = """
/**
 * \ingroup {2}{1}
 *
 * Registers a callback with ID \c id to the function \c callback.
 */
void {0}_register_callback({1} *{0}, uint8_t id, void *callback);
"""
    return func.format(device.get_underscore_name(), device.get_camel_case_name(), device.get_category())

def make_callback_wrapper_declarations():
    func = 'int {0}_callback_wrapper_{1}({2} *{0}, const unsigned char *buffer);\n'

    funcs = '\n'
    for packet in device.get_packets('callback'):
        funcs += func.format(device.get_underscore_name(),
                             packet.get_underscore_name(),
                             device.get_camel_case_name())

    return funcs

def make_files(com_new, directory):
    global device
    device = common.Device(com_new)

    file_name = '{0}_{1}'.format(device.get_category().lower(), device.get_underscore_name())
    
    directory += '/bindings'
    if not os.path.exists(directory):
        os.makedirs(directory)

    c = file('{0}/{1}.c'.format(directory, file_name), "w")
    c.write(make_include_c())
    c.write(make_function_id_defines())
    c.write(make_typedefs())
    c.write(make_structs())
    c.write(make_method_funcs())
    c.write(make_callback_wrapper_funcs())
    c.write(make_register_callback_func())
    c.write(make_create_func())

    h = file('{0}/{1}.h'.format(directory, file_name), "w")
    h.write(make_include_h())
    h.write(make_callback_defines())
    h.write(make_create_declaration())
    h.write(make_method_declarations())
    h.write(make_register_callback_declaration())
    h.write(make_end_h())

if __name__ == "__main__":
    common.generate(os.getcwd(), make_files)
