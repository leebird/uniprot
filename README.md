# uniprot
Parse utility for UniProt bulk download files

# Usage

## Generate UniProt AC to Entrez ID mapping
First, downlowd id mapping file (uniprot AC to entrez ID) from UniProt website.
URL: ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/
File: id_mapping.dat.gz


Then use `python extract_ac_to_entrez.py /path/to/id_mapping.dat.gz` to generate a pickled file under the same folder.

## Generate UniProt json dump
Secondly, download Uniprot dump in XML format from https://www.uniprot.org/downloads (Reviewed (Swiss-Prot))
Use `python parser.py /path/to/uniprot_xml_file` to generate a json dump of the uniprot data. 

`parser.py` will use the mapping generated in the first step and assume it's under the same folder (look at the end of `parser.py` for more details)
