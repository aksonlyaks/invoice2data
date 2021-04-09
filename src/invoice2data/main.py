#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import shutil
import os
from os.path import join
import logging
import sys
import copy 

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
                cmdlist = copy.deepcopy(cmdlist_psm6)

        # print(templates[0])
        extracted_str = input_module.to_text(invoicefile, cmdlist=cmdlist, conv_cmdlist=conv_cmdlist).decode("utf-8")

        logger.debug("START pdftotext result ===========================")
        logger.error(extracted_str)
        logger.debug("END pdftotext result =============================")

        logger.debug("Testing {} template files".format(len(templates)))
        if t == None:
            logger.error(f'Searching template based on Keyword')
            for t in templates:
                optimized_str = t.prepare_input(extracted_str)

                if t.matches_input(optimized_str):
                    return t.extract(optimized_str)
        else:
            optimized_str = t.prepare_input(extracted_str) 
            return t.extract(optimized_str)

        logger.error("No template for %s", invoicefile)
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
        res = extract_data(f.name, templates=templates, input_module=args.input_reader, cmdlist=cmdlist, conv_cmdlist=imgcmd, tid=args.tid)
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

if __name__ == "__main__":
    main()
