#
# Copyright 2015 Zuza Software Foundation
# Copyright 2015 Sarah Hale
#
# This file is part of translate.
#
# translate is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# translate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""Convert .Net Resource (.resx) to Gettext PO localisation files.

See: http://docs.translatehouse.org/projects/translate-toolkit/en/latest/commands/resx2po.html
for examples and usage instructions.
"""

import logging

from translate.storage import po


logger = logging.getLogger(__name__)


class resx2po:
    """Convert a RESX file to a PO file for handling translation"""

    def convert_store(self, input_store, duplicatestyle="msgctxt"):
        """Converts a RESX file to a PO file"""
        output_store = po.pofile()
        output_header = output_store.init_headers(
            charset="UTF-8", encoding="8bit", x_accelerator_marker="&"
        )
        output_header.addnote("extracted from %s" % input_store.filename, "developer")
        for input_unit in input_store.units:
            if input_unit.istranslatable():
                output_unit = self.convert_unit(input_unit, "developer")
                if output_unit is not None:
                    # Split out translator & dev comments before adding them
                    self.split_comments(output_unit, output_unit)

                    output_store.addunit(output_unit)

        output_store.removeduplicates(duplicatestyle)
        return output_store

    def merge_store(
        self, template_store, input_store, blankmsgstr=False, duplicatestyle="msgctxt"
    ):
        """Converts two RESX files to a PO file"""
        output_store = po.pofile()
        output_header = output_store.init_headers(
            charset="UTF-8", encoding="8bit", x_accelerator_marker="&"
        )
        output_header.addnote(
            f"extracted from {template_store.filename}, {input_store.filename}",
            "developer",
        )

        input_store.makeindex()
        for template_unit in template_store.units:
            origpo = self.convert_unit(template_unit, "developer")

            # try and find a translation of the same name...
            template_unit_name = "".join(template_unit.getlocations())
            if template_unit_name in input_store.locationindex:
                translatedresx = input_store.locationindex[template_unit_name]
                translatedpo = self.convert_unit(translatedresx, "translator")
            else:
                translatedpo = None

            # if we have a valid po unit, get the translation and add it...
            if origpo is not None:
                if translatedpo is not None and not blankmsgstr:
                    origpo.target = translatedpo.source

                    # Split out translator & dev comments before adding them
                    self.split_comments(origpo, translatedpo)

                output_store.addunit(origpo)

            elif translatedpo is not None:
                logger.error("Error converting original RESX definition %s", origpo)

        output_store.removeduplicates(duplicatestyle)
        return output_store

    @staticmethod
    def split_comments(origpo, translatedpo):
        autocomments = translatedpo.getnotes("developer")
        if autocomments:
            devcomment, transcomment = autocomments.partition("[Translator Comment: ")[
                ::2
            ]
            if transcomment:
                origpo.addnote(transcomment.replace("]", ""), origin="translator")
            if devcomment:
                origpo.addnote(devcomment.strip(), origin="developer", position="merge")

    @staticmethod
    def convert_unit(input_unit, commenttype):
        """Converts a RESX unit to a PO unit
        @return: None if empty or not for translation
        """
        if input_unit is None:
            return None

        output_unit = po.pounit(encoding="UTF-8")
        output_unit.addlocation(input_unit.getid())
        output_unit.source = input_unit.source
        output_unit.addnote(input_unit.getnotes("developer"), "developer")
        output_unit.target = ""

        return output_unit


def convert_resx(
    input_file,
    output_file,
    template_file,
    pot=False,
    duplicatestyle="msgctxt",
    filter=None,
):
    from translate.storage import resx

    input_store = resx.RESXFile(input_file)
    convertor = resx2po()
    if template_file is None:
        output_store = convertor.convert_store(
            input_store, duplicatestyle=duplicatestyle
        )
    else:
        template_store = resx.RESXFile(template_file)
        output_store = convertor.merge_store(
            template_store, input_store, blankmsgstr=pot, duplicatestyle=duplicatestyle
        )
    if output_store.isempty():
        return 0
    output_store.serialize(output_file)
    return 1


def main(argv=None):
    from translate.convert import convert

    formats = {
        "resx": ("po", convert_resx),
        ("resx", "resx"): ("po", convert_resx),
    }
    parser = convert.ConvertOptionParser(
        formats, usetemplates=True, usepots=True, description=__doc__
    )
    parser.add_option(
        "",
        "--filter",
        dest="filter",
        default=None,
        help="leaves to extract e.g. 'name,desc': (default: extract everything)",
        metavar="FILTER",
    )
    parser.add_duplicates_option()
    parser.passthrough.append("pot")
    parser.passthrough.append("filter")
    parser.run(argv)


if __name__ == "__main__":
    main()
