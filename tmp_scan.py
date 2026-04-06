import sys

def main():
    try:
        with open(r'data\mt5_symbols_list.txt', 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print("Error reading:", e)
        return

    blocks = text.split('=== SÀN:')
    for block in blocks:
        if not block.strip(): continue
        lines = block.split('\n')
        san_name = lines[0].strip(' =')
        symbols = []
        for line in lines[1:]:
            if line.strip():
                symbols.extend([s.strip() for s in line.split(',')])
                
        nasdaq = [s for s in symbols if any(k in s.upper() for k in ['NAS', 'NDX', 'US100', 'USTEC', 'US_100'])]
        yield10y = [s for s in symbols if any(k in s.upper() for k in ['10Y', 'YIELD', 'TNOTE', 'US10', 'TREASURY'])]
        
        if nasdaq or yield10y:
            print(f'\n[SÀN] {san_name}')
            if nasdaq: print('  => NASDAQ: ' + ', '.join(nasdaq[:20]) + (f' ... ({len(nasdaq)} mã)' if len(nasdaq)>20 else ''))
            if yield10y: print('  => 10Y YIELD: ' + ', '.join(yield10y[:20]) + (f' ... ({len(yield10y)} mã)' if len(yield10y)>20 else ''))

if __name__ == '__main__':
    main()
