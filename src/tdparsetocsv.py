# run the parser
# parse all pdfs in a directory 'statements'

import os
import tdparser

if __name__ == "__main__":
    if not os.path.exists("statements"):
        print("Create a directory named 'statements' and put TD Bank PDF statements in it.")
        exit(1)
    processed_files = 0
    verified_files = 0
    for filename in os.listdir("statements"):
        if filename.endswith(".pdf"):
            full_path = os.path.join("statements", filename)
            print(f"Processing {full_path}")
            df = tdparser.parse_td_pdf(full_path)
            processed_files += 1
            verification_result, verification_details = tdparser.verify_balances(df, full_path)
            if verification_result:
                verified_files += 1
            else:
                print(f"[✗] Balance verification failed for {filename}, Details: {verification_details}")
            if df is not None:
                if not os.path.exists("out"):
                    os.makedirs("out")
                df.to_csv(f"out/{filename[:-4]}.csv", index=False)

    print(f"Processed {processed_files} files")
    print(f"Verified {verified_files} files successfully")
    # if any files failed verification, warn the user
    if verified_files < processed_files:
        print(f"[✗] {processed_files - verified_files} files failed balance verification. Please check the output above for details.")
        