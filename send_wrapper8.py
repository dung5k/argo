import sys
with open('temp_report8.txt', 'r', encoding='utf-8') as f:
    text = f.read()

sys.argv = ['send_to_tele.py', text, '--channel', '1816854047', '--done']
exec(open('.agent/send_to_tele.py', encoding='utf-8').read())
