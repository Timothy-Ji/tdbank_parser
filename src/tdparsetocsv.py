# run the parser
# parse all pdfs in a directory 'statements'

import os
import tdparser

if __name__ == "__main__":
    if not os.path.exists("statements"):
        print("Create a directory named 'statements' and put TD Bank PDF statements in it.")
        exit(1)
    for filename in os.listdir("statements"):
        if filename.endswith(".pdf"):
            df = tdparser.parse_td_pdf(os.path.join("statements", filename))
            tdparser.verify_balances(df, os.path.join("statements", filename))
            if df is not None:
                if not os.path.exists("out"):
                    os.makedirs("out")
                df.to_csv(f"out/{filename[:-4]}.csv", index=False)

        