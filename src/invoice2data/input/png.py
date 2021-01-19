# -*- coding: utf-8 -*-


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
    import subprocess
    from distutils import spawn

    # Check for dependencies. Needs Tesseract and Imagemagick installed.
    if not spawn.find_executable("tesseract"):
        raise EnvironmentError("tesseract not installed.")
    if not spawn.find_executable("convert"):
        raise EnvironmentError("imagemagick not installed.")

    # convert = "convert -density 350 %s -depth 8 tiff:-" % (path)
    #convert = [
    #    "convert",
    #    "-density",
    #    "350",
    #    path,
    #    "-depth",
    #    "8",
    #    "-alpha",
    #    "off",
    #    "tiff:-",
    #]
    #p1 = subprocess.Popen(convert, stdout=subprocess.PIPE)

    #tess = ["tesseract", "-c", "tessedit_char_whitelist=/.: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", path, "stdout"]
    if cmdlist == None:
        tess = [
            "tesseract",
            "-l",
            "eng",
            "--oem",
            "1",
            "--psm",
            "6",
            "-c",
            "tessedit_char_whitelist=#-/.: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            path,
            "stdout",
        ]
    else:
        cmdlist.append(path)
        cmdlist.append("stdout")
        tess = cmdlist
    p2 = subprocess.Popen(tess, stdout=subprocess.PIPE)

    out, err = p2.communicate()

    extracted_str = out

    return extracted_str
