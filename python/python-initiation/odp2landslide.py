"""
Ad hoc script to convert from odp to md

usage: python odp2landslide.py "/full/path/to/the.odp"
"""
# pip install normalizr
# apt install unoconv

from normalizr import Normalizr
import os
import re
import shutil
import sys
import subprocess
import xml.sax
import zipfile

normalizr = Normalizr(language='fr')
HR = "--------------------------------------------------------------------------------\n\n"
URL_PATTERN = re.compile(
    r"""(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\)]|(?:%[0-9a-fA-F][0-9a-fA-F]))+(#[\w\-]*)?)""")
EXTENSIONS_TO_CONVERT = {
    'svm': 'svg'
}


def insert_hr_pattern(text):
    return text.replace('###', HR + '###')


def replace_special_chars(text):
    return text.replace('\xa0', ' ').replace('‘', "'").replace('’', "'")


def mark_links(text):
    return URL_PATTERN.sub(r'<\1>', text)


def normalize_title(title):
    title = title.replace('–', ' ')
    normalizations = [
        'remove_accent_marks',
        'replace_punctuation',
        'remove_extra_whitespaces',
    ]
    return normalizr.normalize(title,
                               normalizations).strip().replace(' ', '-').lower()


def preformat_python(text):
    """Detect python block and mark them as preformated with !python"""
    in_python = False
    output = ""
    for line in text.split('\n'):
        if ">>>" in line:
            if not in_python:
                output += "\n    !python\n"
                in_python = True
        elif line.strip() == "":
            # python block probably ended if we have an empty line
            in_python = False

        if in_python:
            if line.startswith('-'):
                line = line[1:]
            output += "    %s\n" % line.strip()
        else:
            output += line + "\n"

    return output


def convert_picture(picture_rel_path, dest_images_dir):
    """If extension is registered in EXTENSIONS_TO_CONVERT
    create converted file and return new file path.
    """
    picture_path_wo_extension, extension = os.path.splitext(picture_rel_path)
    extension = extension[1:]  # remove "."
    if extension in EXTENSIONS_TO_CONVERT:
        converted_extension = EXTENSIONS_TO_CONVERT[extension]
        converted_rel_path = "%s.%s" % (picture_path_wo_extension,
                                        converted_extension)
        subprocess.call([
            'unoconv',
            '-f', converted_extension,
            '-o', os.path.join(dest_images_dir, converted_rel_path),
            os.path.join(dest_images_dir, picture_rel_path)
        ])

        return converted_rel_path
    else:
        return None


def insert_images(text, images_tuples, images_rel_dest_dir):
    """
    :param text:
    :param images_tuples: tuples: (img_href, previous characters)
    :return:
    """
    filenames = set()

    for img_href, title, previous_chars in reversed(images_tuples):
        extension = os.path.splitext(img_href)[-1]
        filename = '%s%s' % (normalize_title(title), extension)
        n = 0
        while True:
            if filename not in filenames:
                break
            if n == 0:
                filename = filename.replace(extension, '-1' + extension)
            else:
                filename = filename.replace("-%s%s" % (n, extension),
                                            "-%s%s" % (n + 1, extension))
            n += 1

        filenames.add(filename)
        pretty_image_rel_path = os.path.join(images_rel_dest_dir, filename)
        shutil.copy(os.path.join(images_rel_dest_dir, img_href),
                    pretty_image_rel_path)

        # TODO: be lucky
        inserted = """%s
![](%s)
""" % (previous_chars, pretty_image_rel_path)
        text = text.replace(previous_chars, inserted, 1)

    return text


class PicturesSearchHandler(xml.sax.ContentHandler):
    last_characters = None
    first_line = None
    in_title = False
    current_title = None
    pictures = None

    def __init__(self, *args):
        xml.sax.ContentHandler.__init__(self)
        self.pictures = []

    def startElement(self, name, attrs):
        #     self.before_last = self.last_elem
        #     self.last_elem = name
        if attrs:
            if "presentation:class" in attrs.getNames():
                self.in_title = True
            if "xlink:href" in attrs.getNames():
                href = attrs.getValue("xlink:href")
                if href.startswith("Pictures/"):
                    self.pictures.append(
                        (href,
                         self.current_title or self.first_line or 'image',
                         self.last_characters))

    def endElement(self, name):
        pass

    def characters(self, content):
        content = content.strip()
        if content:
            if self.in_title:
                self.current_title = content
                self.first_line = None
                self.in_title = False
            elif not self.first_line:
                self.first_line = content

            self.last_characters = content


if __name__ == '__main__':
    import ipdb; ipdb.set_trace()
    odp_abspath = sys.argv[1]

    src_dir = os.path.dirname(odp_abspath)
    src_md_abspath = os.path.splitext(odp_abspath)[0] + '.md'
    dest_dir = os.path.abspath('.')
    dest_images_rel_dir = 'images'
    dest_images_dir = os.path.join(dest_dir, dest_images_rel_dir)
    dest_md_file = os.path.join(dest_dir, 'index.md')

    # create md source file from odp source file
    subprocess.call(['/home/tde/bin/odp2md', odp_abspath])

    with open(src_md_abspath, 'r') as md_file, zipfile.ZipFile(odp_abspath,
                                                             'r') as archive:
        # extract pictures
        content_xml = archive.open('content.xml').read().decode('utf-8')
        pictures_search_handler = PicturesSearchHandler()
        xml.sax.parseString(content_xml, pictures_search_handler)
        print(pictures_search_handler.pictures)

        pictures_info = []
        for picture_path, section_title, previous_text in pictures_search_handler.pictures:
            archive.extract(picture_path, dest_images_dir)
            converted_picture_path = convert_picture(picture_path,
                                                     dest_images_dir)
            pictures_info.append((converted_picture_path or picture_path,
                                  section_title, previous_text))

        text = md_file.read()

    text = replace_special_chars(text)
    text = insert_hr_pattern(text)
    text = insert_images(text, pictures_info, dest_images_rel_dir)
    text = mark_links(text)
    text = preformat_python(text)

    with open(dest_md_file, 'w') as f:
        f.write(text)
