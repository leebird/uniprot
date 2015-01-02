import sys

if len(sys.argv) < 2:
    print('Usage: python3 remove_xmlns.py filepath')
    sys.exit(0)

filepath = sys.argv[1]

file = open(filepath, 'r')

done_flag = False

for line in file:
    if done_flag:
        print(line, end='')
    elif line == '<uniprot xmlns="http://uniprot.org/uniprot"\n':
        print('<uniprot>')
    elif line.endswith('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'):
        continue
    elif line.endswith(
            'xsi:schemaLocation="http://uniprot.org/uniprot http://www.uniprot.org/support/docs/uniprot.xsd">\n'):
        done_flag = True
        continue