def to_text(path, cmdlist=None):
    """Wraps Tesseract OCR.

    Parameters
    ----------
    path : str
        path of electronic invoice in JPG or PNG format

    Returns
    -------
    extracted_str : str
        returns extracted text from image in JPG or PNG format

    """
    with open(path, "rb") as fp:
        extracted_str = fp.read()

    return extracted_str