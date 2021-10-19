# a little program can convert gcc rlt dump(-fdump-rtl-all) file to .dot file
# then the .dot file can be previewed on http://magjac.com/graphviz-visual-editor/
# author: lhtin(github)
# date: 2021-10-18

import sys
import re
import os

def is_insn(name):
    return name.startswith('insn')

def is_jump_insn(name):
    return name.startswith('jump_insn')

def is_call_insn(name):
    return name.startswith('call_insn')

def get_code(list):
    return list[5] if re.fullmatch('\d+', list[4]) else list[4]

def get_label(code):
    labels = re.findall('\(label_ref(?:[^\s]+)?\s+([0-9]+)\)', code)
    if len(labels) > 1:
        raise Exception('code中的分支多余一个：{0}'.format(labels[0]))
    return labels[0] if len(labels) == 1 else None

def read_one(lines, at):
    arr = []
    i = at
    while i < len(lines):
        line = lines[i]
        # print('line', line)
        for ch in line:
            if ch == '(':
                arr.append(ch)
            elif ch == ')':
                arr.pop()
                if len(arr) == 0:
                    return i - at + 1, lines[at:i + 1]
        i += 1

def read_s_exp(lines):
    line = ''.join(lines)
    # print(line)
    arr = []
    curr = ''
    arr1 = []
    for ch in line:
        if ch == '(' or ch == '[':
            arr1.append(ch)
            if len(arr1) > 1:
                curr += ch
        elif ch == ')' or ch == ']':
            if len(arr1) > 1:
                curr += ch
            if ((ch == ']' and arr1[-1] == '[') or
                (ch == ')' and arr1[-1] == '(')):
                arr1.pop()
            else:
                raise Exception('括号闭合不完整：{0}'.format(line))
            if len(arr1) == 0:
                arr.append(curr)
        elif len(arr1) == 1 and (ch == ' ' or ch == '\n'):
            if curr != '':
                arr.append(curr)
            curr = ''
        else:
            curr += ch
    # print(arr)
    return arr

def read_func(func_name, lines):
    i = 0
    all = {}
    start_item = None
    level = 1
    while i < len(lines):
        line = lines[i] #.strip()
        if (line[0] == '('):
            count, lines1 = read_one(lines, i)
            i += count
            list = read_s_exp(lines1)
            # print('list', list)
            id = list[1]
            item = {
                'list': list,
                'name': list[0],
                'id': list[1],
                'prev': list[2],
                'next': list[3],
                'label_next': '0',
                'bb': '',
                'level': level
            }
            level += 1
            if item['prev'] == '0':
                start_item = id
            all[id] = item
        else: 
            i += 1
    curr_item = start_item
    prev = None
    bb_key = ''
    while curr_item in all:
        item = all[curr_item]
        list = item['list']
        item_name = item['name']

        if item_name == 'note':
            note_name = list[-1]
            if note_name == 'NOTE_INSN_BASIC_BLOCK':
                bb_key = func_name + '_' + list[-2].replace('[', '').replace(']', '').replace(' ', '')
                # print(bb_key, list[-2], list)
                if prev != None:
                    # print('xxx2', prev['next'], item['next'])
                    prev['next'] = item['next']
                else:
                    start_item = item['next']
            else:
                if prev != None:
                    prev['next'] = item['next']
                else:
                    start_item = item['next']
            curr_item = item['next']
        elif item_name == 'barrier':
            prev = item
            curr_item = item['next']
        elif item_name == 'code_label':
            prev = item
            curr_item = item['next']
        elif (is_insn(item_name) or
            is_jump_insn(item_name) or
            is_call_insn(item_name)):
            item['bb'] = bb_key
            if is_jump_insn(item_name):
                code = get_code(list)
                label = get_label(code)
                if label:
                    # print('label', label)
                    item['label_next'] = label
                    # print(item['id'], label)
            prev = item
            curr_item = item['next']
        else:
            item['bb'] = bb_key
            prev = item
            curr_item = item['next']

    # 移除code_label
    for curr_item, item in all.items():
        if item['label_next'] != '0':
            item['label_next'] = all[item['label_next']]['next']

    return start_item, all

def read_func2(func_name, lines):
    edges = []
    bb_map = {}
    big_edges = []
    big_bb = []
    bb_label_map = {}
    outer_nodes = []
    start_item, all = read_func(func_name, lines)
    curr_item = start_item
    while curr_item in all:
        # print(curr_item)
        item = all[curr_item]
        list = item['list']
        bb_key = item['bb']
        insn_name = item['name']
        current_node = '{0}_node_{1}'.format(func_name, item['id'])
        next_item = item['next']
        if bb_key != '' and ('r_' + bb_key) not in big_bb:
            big_bb.append('r_' + bb_key)
        if next_item in all:
            next = all[next_item]
            next_node = '{0}_node_{1}'.format(func_name, next['id'])
            next_name = next['name']
            if next_name == 'code_label':
                next_item = next['next']
                next = all[next_item]
                next_node = '{0}_node_{1}'.format(func_name, next['id'])
                next_name = next['name']
            if next_item in all and insn_name != 'barrier' and next['name'] != 'barrier':
                edges.append(current_node + ' -> ' + next_node)
                if item['bb'] != next['bb']:
                    big_edges.append('{0} -> {1}'.format(item['bb'], next['bb']))
        current_node_with_label = current_node
        label = ''
        if bb_key != '' and bb_key not in bb_label_map:
            bb_label_map[bb_key] = ''
        if is_insn(insn_name) or is_jump_insn(insn_name) or is_call_insn(insn_name):
            code = get_code(list)
            label = '{1} {2}\\r{0}\l\l'.format(code.replace('"', '\\"').replace('\n', '\l'), insn_name, list[1])
            bb_label_map[bb_key] += label
            current_node_with_label += '[label="{0}"]'.format(label)
            if is_jump_insn(insn_name) and item['label_next'] != '0':
                edges.append('{0} -> {1}_node_{2}[label="jump" style=dashed]'.format(current_node, func_name, item['label_next']))
                next = all[item['label_next']]
                if item['bb'] != next['bb']:
                    big_edges.append('{0} -> {1}[label="jump" style=dashed]'.format(item['bb'], next['bb']))
        elif insn_name == 'note':
            current_node_with_label += '[label="{0}_{1}_{2}"]'.format(insn_name, list[1], list[-1])
        elif insn_name == 'barrier':
            current_node_with_label += '[label="{0}_{1}" color=lightgray fontcolor=lightgray]'.format(insn_name, list[1])
        else:
            current_node_with_label += '[label="' + insn_name + '_' + list[1] + '"]'
        if bb_key != '':
            if (bb_key not in bb_map):
                    bb_map[bb_key] = [current_node_with_label]
            else:
                bb_map[bb_key].append(current_node_with_label)
        elif insn_name != 'barrier':
            outer_nodes.append(current_node_with_label)
        curr_item = next_item
    return edges, bb_map, outer_nodes, bb_label_map, big_edges, big_bb

def main(rtl_filename, output_filename, is_big = True):
    with open(rtl_filename, 'r') as rtl_file:
        lines = rtl_file.readlines()
        funcs = []
        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.findall(';; Function ([^\s]+) \([^\s]+, funcdef_no=\d+, decl_uid=\d+, cgraph_uid=(\d+), symbol_order=\d+\)', line)
            if len(m) > 0:
                func_name = m[0][0]
                func_uid = m[0][1]
                funcs.append({
                    'func_name': func_name,
                    'func_uid': func_uid,
                    'start_index': i,
                    'lines': []
                })
            i += 1
        i = 0
        subgraph_list = []
        while i < len(funcs):
            # print(funcs[i])
            func_name = funcs[i]['func_name']
            func_uid = funcs[i]['func_uid']
            start_index = funcs[i]['start_index']
            curr_lines = lines[start_index:funcs[i + 1]['start_index'] if i + 1 < len(funcs) else len(lines)]
            edges, bb_map, outer_nodes, bb_label_map, big_edges, big_bb = read_func2(func_name, curr_lines)
            subgraph = ''
            if is_big:
                outer_nodes = '\n    '.join(list(map(lambda node: f'{node};', outer_nodes)))
                bb_nodes = '\n    '.join(list(map(lambda item: f'{item[0]}[label="{item[1]}" xlabel="{item[0].replace(func_name + "_", "")}"];', bb_label_map.items())))
                edges = '\n    '.join(list(map(lambda edge: f'{edge};', big_edges)))
                rank_nodes = '\n    '.join(list(map(lambda item: f'{{ rank="same"; {"r_" + item[0]}[style=invis fixedsize=true with=0]; {item[0]}; }}', bb_label_map.items())))
                subgraph = f'''
  subgraph cluster_{func_name} {{
    label="{func_name}";

    /* outer nodes */
    {outer_nodes}

    /* bb nodes */
    {bb_nodes}

    /* edges */
    {edges}

    /* rank nodes */
    {rank_nodes}

    /* rank edges */
    {" -> ".join(big_bb)}[style=invis];
  }}
  '''
                subgraph_list.append(subgraph)
            else:
                subgraph += '  subgraph cluster_{0} {{\n    label = "{1}"\n'.format(func_name, func_name)
                for node in outer_nodes:
                    subgraph += '    {0};\n'.format(node)
                for bb_key, bb in bb_map.items():
                    subgraph += '    subgraph cluster_{0} {{\n      label = "{1}"\n      color=gray;\n'.format(bb_key, bb_key.replace(func_name + "_", ""))
                    for node in bb:
                        subgraph += '      {0};\n'.format(node)
                    subgraph += '    }\n'
                for edge in edges:
                    subgraph += '    {0};\n'.format(edge)
                subgraph += '  }\n'
                subgraph_list.append(subgraph)
            i += 1

        rtl_basename = os.path.basename(rtl_filename)
        subgraph_str = '\n'.join(subgraph_list)
        graph = f'''
digraph rtl {{
  labelloc="t";
  label="{rtl_basename}";

  node[shape="box" fontname="Courier" color="gray"];

{subgraph_str}
}}
'''
        if output_filename:
            with open(output_filename, 'w') as output_file:
                output_file.write(graph)
        else:
            print(graph)

rtl_filename = None
output_filename = None
big_dot = True
if len(sys.argv) > 1 and sys.argv[1] == '-help':
    print('''Usage:
    python3 rtl2dot.py path/to/rtl-dump -o path/to/output
    ''')
elif len(sys.argv) > 2 and sys.argv[2] == '-o':
    rtl_filename = sys.argv[1]
    output_filename = sys.argv[3]
    main(rtl_filename, output_filename, big_dot)
elif len(sys.argv) > 1:
    rtl_filename = sys.argv[1]
    main(rtl_filename, output_filename, big_dot)
