# -*- coding: utf-8 -*-
#
#
# Project name: OpenVAS Reporting: A tool to convert OpenVAS XML reports into Excel files.
# Project URL: https://github.com/TheGroundZero/openvas_to_report

import sys
import logging

from .config import Config
from .parsed_data import Host, Port, Vulnerability

# logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
#                     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logging.basicConfig(stream=sys.stderr, level=logging.ERROR,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

__all__ = ["openvas_parser"]

try:
    from xml.etree import cElementTree as Et
except ImportError:
    from xml.etree import ElementTree as Et


def openvas_parser(input_files, min_lvl=Config.levels()["n"]):
    """
    This function takes an OpenVAS XML report and returns Vulnerability info

    :param input_files: path to XML files
    :type input_files: list(str)

    :param min_lvl: Minimal level (none, low, medium, high, critical) for displaying vulnerabilities
    :type min_lvl: str

    :return: list

    :raises: TypeError, InvalidFormat
    """
    if not isinstance(input_files, list):
        raise TypeError("Expected list, got '{}' instead".format(type(input_files)))
    else:
        for file in input_files:
            if not isinstance(file, str):
                raise TypeError("Expected basestring, got '{}' instead".format(type(file)))
            with open(file, "r", newline=None) as f:
                first_line = f.readline()
                if not first_line.startswith("<report") or \
                        not all(True for x in ("extension", "format_id", "content_type") if x in first_line):
                    raise IOError("Invalid report format")

    if not isinstance(min_lvl, str):
        raise TypeError("Expected basestring, got '{}' instead".format(type(min_lvl)))

    vulnerabilities = {}

    for f_file in input_files:
        root = Et.parse(f_file).getroot()

        logging.debug("================================================================================")
        logging.debug("= {}".format(root.find("./task/name").text))  # DEBUG
        logging.debug("================================================================================")

        for vuln in root.findall(".//results/result"):

            nvt_tmp = vuln.find(".//nvt")

            # VULN_NAME
            vuln_name = nvt_tmp.find(".//name").text

            logging.debug("--------------------------------------------------------------------------------")
            logging.debug("- {}".format(vuln_name))  # DEBUG
            logging.debug("--------------------------------------------------------------------------------")

            # --------------------
            #
            # VULN_ID
            vuln_id = nvt_tmp.get("oid")
            if not vuln_id or vuln_id == "0":
                continue
            logging.debug("* vuln_id:\t{}".format(vuln_id))  # DEBUG

            # --------------------
            #
            # VULN_CVSS
            vuln_cvss = vuln.find(".//severity").text
            if vuln_cvss is None:
                vuln_cvss = 0.0
            vuln_cvss = float(vuln_cvss)
            logging.debug("* vuln_cvss:\t{}".format(vuln_cvss))  # DEBUG

            # --------------------
            #
            # VULN_LEVEL
            if vuln_cvss < 0.1:
                vuln_level = Config.levels()["n"]
                if min_lvl not in Config.levels()["n"]:
                    continue
            elif vuln_cvss < 4:
                vuln_level = Config.levels()["l"]
                if min_lvl not in (Config.levels()["n"], Config.levels()["l"]):
                    continue
            elif vuln_cvss < 7:
                vuln_level = Config.levels()["m"]
                if min_lvl not in (Config.levels()["n"], Config.levels()["l"], Config.levels()["m"]):
                    continue
            elif vuln_cvss < 9:
                vuln_level = Config.levels()["h"]
                if min_lvl not in (Config.levels()["n"], Config.levels()["l"], Config.levels()["m"],
                                   Config.levels()["h"]):
                    continue
            else:
                vuln_level = Config.levels()["c"]

            logging.debug("* vuln_level:\t{}".format(vuln_level))  # DEBUG

            # --------------------
            #
            # VULN_LEVEL >= MIN_LEVEL (param)?
            if (min_lvl == Config.levels()["c"] and vuln_level not in (Config.levels()["c"])) or \
                    (min_lvl == Config.levels()["h"] and vuln_level not in (Config.levels()["c"],
                                                                            Config.levels()["h"])) or \
                    (min_lvl == Config.levels()["m"] and vuln_level not in (Config.levels()["c"],
                                                                            Config.levels()["h"],
                                                                            Config.levels()["m"])) or \
                    (min_lvl == Config.levels()["l"] and vuln_level not in (Config.levels()["c"],
                                                                            Config.levels()["h"],
                                                                            Config.levels()["m"],
                                                                            Config.levels()["l"])):
                logging.debug("  ==> SKIP")  # DEBUG
                continue

            # --------------------
            #
            # VULN_HOST
            vuln_host = vuln.find(".//host").text
            vuln_port = vuln.find(".//port").text
            logging.debug("* vuln_host:\t{} port:\t{}".format(vuln_host, vuln_port))  # DEBUG

            # --------------------
            #
            # VULN_DESCRIPTION
            vuln_description = vuln.find(".//description").text
            logging.debug("* vuln_desc:\t{}".format(vuln_description))  # DEBUG

            # --------------------
            #
            # VULN_THREAT
            vuln_threat = vuln.find(".//threat").text
            if vuln_threat is None:
                vuln_threat = Config.levels()["n"]
            else:
                vuln_threat = vuln_threat.lower()

            logging.debug("* vuln_threat:\t{}".format(vuln_threat))  # DEBUG

            # --------------------
            #
            # VULN_FAMILY
            vuln_family = nvt_tmp.find(".//family").text

            logging.debug("* vuln_family:\t{}".format(vuln_family))  # DEBUG

            # --------------------
            #
            # VULN_CVES
            vuln_cves = nvt_tmp.find(".//cve").text
            if vuln_cves:
                if vuln_cves.lower() == "nocve":
                    vuln_cves = []
                else:
                    vuln_cves = [vuln_cves.lower()]

            logging.debug("* vuln_cves:\t{}".format(vuln_cves))  # DEBUG

            # --------------------
            #
            # VULN_REFERENCES
            vuln_references = nvt_tmp.find(".//xref").text
            if vuln_references:
                if vuln_references.lower() == "noxref":
                    vuln_references = []
                else:
                    tmp1 = vuln_references.strip().lower()
                    tmp1_init = tmp1.find("url:")
                    tmp2 = tmp1[tmp1_init + 4:].split(",")
                    vuln_references = [x.strip() for x in tmp2]

            logging.debug("* vuln_references:\t{}".format(vuln_references))  # DEBUG

            # --------------------
            #
            # STORE VULN_HOSTS PER VULN
            host = Host(vuln_host)
            try:
                port = Port.string2port(vuln_port)
            except ValueError:
                port = None

            try:
                vuln_store = vulnerabilities[vuln_id]
            except KeyError:
                vuln_store = Vulnerability(vuln_id,
                                           name=vuln_name,
                                           threat=vuln_threat,
                                           description=vuln_description,
                                           cvss=vuln_cvss,
                                           cves=vuln_cves,
                                           references=vuln_references,
                                           family=vuln_family,
                                           level=vuln_level)

            vuln_store.add_vuln_host(host, port)
            vulnerabilities[vuln_id] = vuln_store

    return list(vulnerabilities.values())
