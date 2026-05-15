import sys, re

filepath = r'd:\DungLA\client1\src\training_v6\train_v6.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('Ã°Å¸â€”â€˜Ã¯Â¸', '🗑️')
content = content.replace('Ã„ ang xÃƒÂ³a thÃ†Â° mÃ¡Â»Â¥c Run rÃƒÂ¡c Ã„â€˜Ã¡Â»Æ’ tiÃ¡ÂºÂ¿t kiÃ¡Â»â€¡m Ã¡Â»â€¢ cÃ¡Â»Â©ng:', 'Đang xóa thư mục Run rác để tiết kiệm ổ cứng:')
content = content.replace('Ã¢Å“â€¦ Ã„ ÃƒÂ£ xÃƒÂ³a thÃƒÂ nh cÃƒÂ´ng run rÃƒÂ¡c:', '✅ Đã xóa thành công run rác:')
content = content.replace('Ã„ ÃƒÂ£ xÃƒÂ³a Run rÃƒÂ¡c', 'Đã xóa Run rác')
content = content.replace('ThÃ†Â° mÃ¡Â»Â¥c:', 'Thư mục:')
content = content.replace('LÃƒÂ½ do:', 'Lý do:')
content = content.replace('Ã¢ Å’ LÃ¡Â»â€”i khi xÃƒÂ³a run rÃƒÂ¡c:', '❌ Lỗi khi xóa run rác:')
content = content.replace('Ã°Å¸Â â€ ', '🏆')
content = content.replace('Ã„ ang PUSH lÃƒÂªn HuggingFace...', 'Đang PUSH lên HuggingFace...')
content = content.replace('Ã¢Å“â€¦ Ã„ ÃƒÂ£ Push thÃƒÂ nh cÃƒÂ´ng!', '✅ Đã Push thành công!')
content = content.replace('Ã¢ËœÂ Ã¯Â¸', '☁️')
content = content.replace('Ã„ ÃƒÂ£ Ã„â€˜Ã¡Â»â€œng bÃ¡Â»â„¢ lÃƒÂªn HF', 'Đã đồng bộ lên HF')
content = content.replace('Ã¢ Å’ LÃ¡Â»â€”i khi Push:', '❌ Lỗi khi Push:')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
