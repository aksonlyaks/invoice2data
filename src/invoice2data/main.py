#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import shutil
import os
from os.path import join
import logging
import sys
import copy 
import re

from .input import pdftotext
from .input import pdfminer_wrapper
from .input import tesseract
from .input import tesseract4
from .input import gvision
from .input import txt
from .input import png

from invoice2data.extract.loader import read_templates

from .output import to_csv
from .output import to_json
from .output import to_xml
from invoice2data.decorators import timeit


logger = logging.getLogger(__name__)

input_mapping = {
    "pdftotext": pdftotext,
    "tesseract": tesseract,
    "tesseract4": tesseract4,
    "pdfminer": pdfminer_wrapper,
    "gvision": gvision,
    "txt": txt,
    "png": png,
}

output_mapping = {"csv": to_csv, "json": to_json, "xml": to_xml, "none": None}
cmdlist_psm3 = ["tesseract", "-c", "tessedit_char_whitelist=/.: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"]
cmdlist_psm6 = ["tesseract", "-l", "eng", "--oem", "1", "--psm", "6", "-c", "tessedit_char_whitelist=#-/%.:, abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"]

@timeit
def extract_data(invoicefile, templates=None, input_module="png", cmdlist=None, conv_cmdlist=None, tid=None):
    """Extracts structured data from PDF/image invoices.
˜
    This function uses the text extracted from a PDF file or image and
    pre-defined regex templates to find structured data.

    Reads template if no template assigned
    Required fields are matches from templates

    Parameters
    ----------
    invoicefile : str
        path of electronic invoice file in PDF,JPEG,PNG (example: "/home/duskybomb/pdf/invoice.pdf")
    templates : list of instances of class `InvoiceTemplate`, optional
        Templates are loaded using `read_template` function in `loader.py`
    input_module : {'pdftotext', 'pdfminer', 'tesseract'}, optional
        library to be used to extract text from given `invoicefile`,

    Returns
    -------
    dict or False
        extracted and matched fields or False if no template matches

    Notes
    -----
    Import required `input_module` when using invoice2data as a library

    See Also
    --------
    read_template : Function where templates are loaded
    InvoiceTemplate : Class representing single template files that live as .yml files on the disk

    Examples
    --------
    When using `invoice2data` as an library

    >>> from invoice2data.input import pdftotext
    >>> extract_data("invoice2data/test/pdfs/oyo.pdf", None, pdftotext)
    {'issuer': 'OYO', 'amount': 1939.0, 'date': datetime.datetime(2017, 12, 31, 0, 0), 'invoice_number': 'IBZY2087',
     'currency': 'INR', 'desc': 'Invoice IBZY2087 from OYO'}

    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    try:
        t = None
        if templates is None:
            templates = read_templates()

        input_module = input_mapping[input_module]
        
        logger.error("Input tid is %s and Input module is %s", tid, input_module)
        for tt in templates:
            if t != None:
                break
            if "tid" in tt.options:
                for tid_option in tt.options["tid"]:
                    if str(tid_option) == tid:
                        t = tt
                        logger.error(f'Template found based on tid {t.options["tid"]} {t["issuer"]}')
                        
                
        if t != None and "psm" in t.options:
            logger.error("PSM is %d", t.options["psm"])
            if str(t.options["psm"]) == "3":
                cmdlist = copy.deepcopy(cmdlist_psm3)
            else:
                cmdlist_psm6[6] = str(t.options["psm"])
                cmdlist = copy.deepcopy(cmdlist_psm6)
        
        if t!=None and "imgcmd" in t.options:
            logger.error("imgcmd is %s", t.options["imgcmd"])
            conv_cmdlist = t.options["imgcmd"]
            
        # print(templates[0])
        extracted_str = input_module.to_text(invoicefile, cmdlist=cmdlist, conv_cmdlist=conv_cmdlist).decode("utf-8")

        logger.debug("START pdftotext result ===========================")
        logger.error(extracted_str)
        logger.debug("END pdftotext result =============================")

        logger.debug("Testing {} template files".format(len(templates)))
        missed = -1
        corrected = -1
        issue_lines = []
        qtyerr = ""
        noofitem = -1
        output = []
        if t == None:
            for t in templates:
                optimized_str = t.prepare_input(extracted_str)

                if t.matches_input(optimized_str):
                    return t.extract(optimized_str)
        else:
            optimized_str = t.prepare_input(extracted_str) 
            output = t.extract(optimized_str)
            if t != None and "decimal" in t.options:
                missed, corrected, issue_lines, qtyerr, noofitem = post_process(output, t.options)
            
            return output, missed, corrected, issue_lines, qtyerr, noofitem

        logger.error("No template for %s", invoicefile)
        return output, missed, corrected, issue_lines, qtyerr, noofitem
    except Exception as ex:
        logger.error("Exception occured in invoice conversion "+ str(ex))

    return False


def create_parser():
    """Returns argument parser """

    parser = argparse.ArgumentParser(
        description="Extract structured data from PDF files and save to CSV or JSON."
    )

    parser.add_argument(
        "--input-reader",
        choices=input_mapping.keys(),
        default="pdftotext",
        help="Choose text extraction function. Default: pdftotext",
    )

    parser.add_argument(
        "--output-format",
        choices=output_mapping.keys(),
        default="none",
        help="Choose output format. Default: none",
    )

    parser.add_argument(
        "--output-date-format",
        dest="output_date_format",
        default="%Y-%m-%d",
        help="Choose output date format. Default: %%Y-%%m-%%d (ISO 8601 Date)",
    )

    parser.add_argument(
        "--output-name",
        "-o",
        dest="output_name",
        default="invoices-output",
        help="Custom name for output file. Extension is added based on chosen format.",
    )

    parser.add_argument(
        "--debug", dest="debug", action="store_true", help="Enable debug information."
    )

    parser.add_argument(
        "--copy",
        "-c",
        dest="copy",
        help="Copy and rename processed PDFs to specified folder.",
    )

    parser.add_argument(
        "--move",
        "-m",
        dest="move",
        help="Move and rename processed PDFs to specified folder.",
    )

    parser.add_argument(
        "--filename-format",
        dest="filename",
        default="{date} {invoice_number} {desc}.pdf",
        help="Filename format to use when moving or copying processed PDFs."
        'Default: "{date} {invoice_number} {desc}.pdf"',
    )

    parser.add_argument(
        "--template-folder",
        "-t",
        dest="template_folder",
        help="Folder containing invoice templates in yml file. Always adds built-in templates.",
    )

    parser.add_argument(
        "--exclude-built-in-templates",
        dest="exclude_built_in_templates",
        default=False,
        help="Ignore built-in templates.",
        action="store_true",
    )

    parser.add_argument(
        "input_files",
        type=argparse.FileType("r"),
        nargs="+",
        help="File or directory to analyze.",
    )

    parser.add_argument(
        "--cmdlist",
        dest="cmdlist",
        default="tesseract,-c,tessedit_char_whitelist=#-/.: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        help="cmdlist for tesseract",
    )
    
    parser.add_argument(
        "--imgcmd",
        dest="imgcmd",
        #default="tesseract,-c,tessedit_char_whitelist=#-/.: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        help="cmdlist for image processing",
    )

    parser.add_argument(
        "--tid",
        dest="tid",
        #default="tesseract,-c,tessedit_char_whitelist=#-/.: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        help="cmdlist for image processing",
    )

    return parser

def generate_output(output, output_name="invoices-output", output_date_format="%Y-%m-%d", output_module=None):
    if output_module is not None:
        output_module = output_mapping[output_module]
        output_module.write_to_file(output, output_name, output_date_format)

def main(args=None):
    """Take folder or single file and analyze each."""
    if args is None:
        parser = create_parser()
        args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cmdlist:
        cmdlist = args.cmdlist.split("+")
    if args.imgcmd:
        imgcmd = args.imgcmd.split("+")
    else:
        imgcmd = None
    templates = []
    # Load templates from external folder if set.
    if args.template_folder:
        templates += read_templates(os.path.abspath(args.template_folder))

    # Load internal templates, if not disabled.
    if not args.exclude_built_in_templates:
        templates += read_templates()
    output = []

    for f in args.input_files:
        res, missed, corrected, issue_lines, qtyerr, noofitem = extract_data(f.name, templates=templates, input_module=args.input_reader, cmdlist=cmdlist, conv_cmdlist=imgcmd, tid=args.tid)
        if res:
            logger.info(res)
            output.append(res)
            if args.copy:
                filename = args.filename.format(
                    #date=res["date"].strftime("%Y-%m-%d"),
                    date=res["date"],
                    invoice_number=res["invoice_number"],
                    desc=res["desc"],
                )
                shutil.copyfile(f.name, join(args.copy, filename))
            if args.move:
                filename = args.filename.format(
                    date=res["date"],
                    invoice_number=res["invoice_number"],
                    desc=res["desc"],
                )
                shutil.move(f.name, join(args.move, filename))
        f.close()

    generate_output(output, output_name=args.output_name, output_date_format=args.output_date_format, output_module=args.output_format)

    sys.exit(missed)

def post_process(output, options):
    option = options['decimal']
    pattern_qty = "(\d+)\W?(\d{%d}).*" % option[0]['qty']
    pattern_rate = "(\d+)\W?(\d{%d}).*" % option[0]['rate']
    pattern_total = "(\d+)\W?(\d{%d}).*" % option[0]['total']
    pattern_totalqty = "(\d+)\W?(\d{%d}).*" % option[0]['totalqty']
            
    if 'totalqty' in output:
        output['totalqty'] = re.sub(pattern_totalqty, r'\1.\2', output['totalqty'])
    
    count = 0
    corrected = 0
    issue_lines = []
    qtyerr = ""
    noofitem = 0
    missed = -1
    issue_lines = []
    if 'lines' in output:
        for items in output['lines']:
            if 'qty' in items:
                items['qty'] = re.sub(pattern_qty, r'\1.\2', items['qty'])
            if 'rate' in items:
                items['rate'] = re.sub(pattern_rate, r'\1.\2', items['rate'])
            if 'total' in items:
                items['total'] = re.sub(pattern_total, r'\1.\2', items['total'])

            logger.info("-----------------------------")
            if 'description' in items:
                logger.info(str(count)+". "+ items['description'])
            else:
                logger.info("Description missing")
                continue
            
            if 'rate' in items:
                if re.search("[^0-9^\.]", items['rate']):
                    logger.info("Error: Rate contains string "+items['rate'])
                    items['rate'] = stringinvalue_correction(items['rate'])
                    logger.info("Error: Rate after correction "+items['rate'])

                elif float(items['rate']) == 0.0:
                    logger.info("Error: Rate is zero")

            if 'gst' in items:
                if re.search("[^0-9^\.]", items['gst']):
                    logger.info("GST contains string")
            
            if 'qty' in items:
                if re.search("[^0-9^\.]", items['qty']):
                    logger.info("Error: qty contains string "+items['qty'])
                    items['qty'] = stringinvalue_correction(items['qty'])
                    logger.info("Error: qty after correction "+items['qty'])
                elif float(items['qty']) == 0.0:
                    logger.info("Error: Quantity is zero")

            if 'total' in items:
                if re.search("[^0-9^\.]", items['total']):
                    logger.info("Error: Total contains string "+items['total'])
                    items['total'] = stringinvalue_correction(items['total'])
                    logger.info("Error: total after correction "+items['total'])

                elif float(items['total']) == 0.0:
                    logger.info("Error: Total is zero")

            err, prod, tot = test_line_basedontotal(items)
            logger.info(f"Qty*rate = {prod} and total = {tot} -- {err} ")

            if (err == "NoMatch") and (options['correction_priority'] == 'qty'):
                correct_qty(items)

                err, prod, tot = test_line_basedontotal(items)
                logger.info(f"After Correction Qty*rate = {prod} and total = {tot} -- {err} ")
                
                if err == "NoMatch":
                    issue_lines.append(count)
                else:
                    corrected = corrected + 1

            count = count + 1
        
        missed = 0
        if 'noofitem' in output:
            if output['noofitem']:
                noofitem = float(output['noofitem'])
            if output['noofitem'] and int(output['noofitem']) != count:
                missed = int(output['noofitem']) - count
                logger.error(f'Error: Missed {missed} while parsing')
        
        if 'totalqty' in output:
            qtyerr, totalqty = test_qty_basedontotalqty(output, output['totalqty'])
            logger.error(f"Total calculated qty {totalqty} and total qty captured {output['totalqty']} -- {qtyerr} ")

        logger.info("-----------------------------")

    return missed, corrected, issue_lines, qtyerr, noofitem

def correct_qty(items):          
     items['qty'] = str(("{:.2f}".format(float(items['total'])/float(items['rate']))))

def stringinvalue_correction(str_val):
    if str_val[0] == "O" or str_val[0] == "o" or str_val[0] == "Q":
        str_val = "0." + str_val[1:]
    else:
        str_val = "0.0"
    
    if re.search("[^0-9^\.]", str_val):
        str_val = "0.0"
    return str_val

def test_line_basedontotal(line_item):
    product_of_qtyrate = "{:.2f}".format(float(line_item['qty']) * float(line_item['rate']))
    total_of_item = "{:.2f}".format(float(line_item['total']))
    if abs(float(product_of_qtyrate) - float(total_of_item)) <= 1:
        return "Match", product_of_qtyrate, total_of_item
    else:
        return "NoMatch", product_of_qtyrate, total_of_item

def test_qty_basedontotalqty(items, totalqty):
    total_qty = 0.0
    for line in items['lines']:
        total_qty = total_qty + float(line['qty'])

    if abs(total_qty - float(totalqty)) <= 1:
        return "Match", "{:.2f}".format(total_qty)
    else:
        return "NoMatch", "{:.2f}".format(total_qty)


if __name__ == "__main__":
    main()
