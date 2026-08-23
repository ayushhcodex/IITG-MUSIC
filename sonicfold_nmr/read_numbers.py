import sys
try:
    from numbers_parser import Document
    import pandas as pd
except ImportError:
    print("numbers-parser or pandas not installed")
    sys.exit(1)

doc = Document("/Users/ayushsingh/developer/iitg-music/CHEMICAL SHIFT PART 1/CHEMICAL SHIFT VALUE V1.numbers")
for sheet in doc.sheets:
    print(f"Sheet: {sheet.name}")
    for table in sheet.tables:
        df = pd.DataFrame(table.rows(values_only=True))
        print(df.head())
        print("Columns: ", df.iloc[0].values if len(df) > 0 else "None")
