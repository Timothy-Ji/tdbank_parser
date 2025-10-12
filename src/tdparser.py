from datetime import datetime
import re
import pandas
import pdfplumber
import os

## Sections
# Deposits
# Electronic Deposits
# Other Credits
# Checks Paid
# Electronic Payments
# Other Withdrawals
# Service Charges

credit_sections = ["Deposits", "Electronic Deposits", "Other Credits"] # Credit
debit_sections = ["Electronic Payments", "Other Withdrawals", "Service Charges"] # Debit
check_sections = ["Checks Paid"] # Debit. Special handling for Checks Paid.

sections = credit_sections + debit_sections + check_sections

## Transaction
# Date 
# Account
# Transaction Type
# Description
# Debit
# Credit

def add_transaction(transactions, date, account_number, current_section, description, debit="", credit=""):
    transactions.append({
        "Date": date,
        "Account": account_number,
        "Transaction Type": current_section,
        "Description": description,
        "Debit": debit,
        "Credit": credit
    })

def detect_section_change(line, current_section):
    # Return current section if line indicates a section change
    # If line is Subtotal: [<amount>], return None to indicate end of section
    # Print the detected section for debugging (Processing: <section>)
    line = line.strip()
    for section in sections:
        if line.startswith(section.replace(" ", "")):
            return section
    if line.startswith("Subtotal:"):
        return None
    return current_section

def is_date_token(tok):
    tok = tok.strip()
    # matches 1/2, 01/02, 1/2/2020, 01/02/20 etc.
    return bool(re.match(r'^\d{1,2}/\d{1,2}(?:/\d{2,4})?$', tok))


def is_footer_line(line):
    return line.startswith("Call 1-800-937-2000")
    

def parse_td_pdf(file_path):
    transactions = []
    with pdfplumber.open(file_path) as pdf:
        # capture account number from first page
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        account_number = None
        for line in text.split("\n"):
            if "PrimaryAccount#: " in line:
                account_number = line.split()[-1]
                break
        if not account_number:
            raise ValueError("Account number not found in the first page")
        # Remove any non-digit characters from account number
        account_number = ''.join(filter(str.isdigit, account_number))

        # ignore data before DAILYACCOUNTACTIVITY
        # end parsing after DAILYBALANCESUMMARY (no more transactions after this)
        transactions_started = False
        allow_continuation = False
        current_section = None
        for page in pdf.pages:
            # TD Bank pages will have DAILYACCOUNTACTIVITY and section header before transactions

            transactions_started = False
            current_section = None
            allow_continuation = False
            # Checks Paid section is special. A line can have two checks (3 columns each), however the chronological order is per individual page, top down, left to right.
            # So we need special handling for this section.
            # It should capture the checks into separate columns and then combine them in the correct order.

            check_columns = []
            text = page.extract_text()
            lines = text.split("\n")
            for line in lines:
                if "DAILYACCOUNTACTIVITY" in line:
                    transactions_started = True
                    continue
                if "DAILYBALANCESUMMARY" in line:
                    transactions_started = False
                    break
                if not transactions_started:
                    continue
                
                # Stop processing page if we hit the footer line
                if is_footer_line(line):
                    break

                # skip line if header line
                if line.startswith("POSTINGDATE") or line.startswith("DATE"):
                    continue

                # if last section was Checks Paid, flush any remaining check columns
                last_section = current_section
                current_section = detect_section_change(line, current_section)

                # skip line if line is a section change or end of section
                if current_section != last_section:
                    allow_continuation = False
                    # flush check columns if we are leaving Checks Paid section
                    if check_columns and last_section in check_sections:
                        transactions.extend(check_columns)
                        check_columns = []
                    continue
                if current_section is None:
                    continue
                
                parts = line.split()

                # if the first token isn't a date, treat this line as a continuation
                if not parts:
                    continue
                if not is_date_token(parts[0]) and allow_continuation:
                    # continuation line: append to previous transaction's Description if exists
                    if transactions:
                        prev = transactions[-1]
                        prev_desc = prev.get("Description", "")
                        # ensure spacing and strip leading/trailing whitespace
                        prev["Description"] = (prev_desc + " " + line.strip()).strip()
                    continue

                if current_section in credit_sections and len(parts) >= 3:
                    date, description, amount = parts[0], ' '.join(parts[1:-1]), parts[-1]
                    add_transaction(transactions, date, account_number, current_section, description, credit=amount.replace(",", ""))
                    allow_continuation = True
                elif current_section in debit_sections and len(parts) >= 3:
                    date, description, amount = parts[0], ' '.join(parts[1:-1]), parts[-1]
                    add_transaction(transactions, date, account_number, current_section, description, debit=amount.replace(",", ""))
                    allow_continuation = True
                elif current_section in check_sections:
                    # Special handling for check sections
                    if len(parts) == 3:
                        date, description, amount = parts[0], parts[1], parts[2]
                        add_transaction(transactions, date, account_number, current_section, description, debit=amount.replace(",", ""))
                    elif len(parts) == 6:
                        # Two checks on the same line
                        date1, description1, amount1 = parts[0:3]
                        date2, description2, amount2 = parts[3:6]
                        add_transaction(transactions, date1, account_number, current_section, description1, debit=amount1.replace(",", ""))
                        add_transaction(check_columns, date2, account_number, current_section, description2, debit=amount2.replace(",", ""))

            # flush any remaining check columns at the end of the page
            if check_columns:
                transactions.extend(check_columns)
                check_columns = []
    # save all transactions to a CSV for inspection
    os.makedirs("out", exist_ok=True)
    return pandas.DataFrame(transactions)

# function to verify if beginning balance - ending balance equals sum of credits - sum of debits
def verify_balances(df, file_path):
    if df.empty:
        print("No transactions found.")
        return
    # Convert Debit and Credit columns to numeric, removing commas and handling empty strings
    df['Debit'] = pandas.to_numeric(df['Debit'].str.replace(',', ''), errors='coerce').fillna(0)
    df['Credit'] = pandas.to_numeric(df['Credit'].str.replace(',', ''), errors='coerce').fillna(0)

    total_debits = df['Debit'].sum()
    total_credits = df['Credit'].sum()
    net_change = total_credits - total_debits

    # Extract beginning and ending balances from the PDF text
    beginning_balance = None
    ending_balance = None
    with pdfplumber.open(file_path) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        for line in text.split("\n"):
            parts = line.split()
            # 1 part index after BeginningBalance and EndingBalance is the amount
            for i in range(len(parts)):
                part = parts[i]
                if part.startswith("EndingBalance") or part.startswith("BeginningBalance"):
                    # next part is the amount
                    if i + 1 < len(parts):
                        amount_str = parts[i + 1].replace(",", "")
                        try:
                            amount = float(amount_str)
                            if part.startswith("EndingBalance"):
                                ending_balance = amount
                            else:
                                beginning_balance = amount
                        except ValueError:
                            continue

    if beginning_balance is None or ending_balance is None:
        print("Could not find beginning or ending balance in the statement.")
        return

    calculated_ending_balance = beginning_balance + net_change

    return abs(calculated_ending_balance - ending_balance) < 0.01, {
        "Beginning Balance": beginning_balance,
        "Ending Balance": ending_balance,
        "Calculated Ending Balance": calculated_ending_balance,
        "Total Credits": total_credits,
        "Total Debits": total_debits
    }