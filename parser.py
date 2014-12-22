import sys
from xml.etree import ElementTree
import json
from pprint import pprint


class TextParser(object):
    def break_line(line):
        line = line.strip("; \n")
        tokens = line.split("   ")
        return tokens

    def parse(self):
        if len(sys.argv) < 2:
            print("specify text file")
        sys.exit(1)
        text_file = sys.argv[1]
        f = open(text_file, "r")

        gene = {}
        count = 0
        for line in f:
            if line.startswith("//"):
                count += 1
                print(gene)
                gene = {}
                if count == 100:
                    break
            elif line.startswith("AC"):
                tokens = break_line(line)
                gene["AC"] = tokens[1]
            elif line.startswith("DE"):
                tokens = break_line(line)
                gene["protein_name"] = tokens[1]
            elif line.startswith("GN"):
                tokens = break_line(line)
                gene["gene_name"] = tokens[1]
            elif line.startswith("OS"):
                tokens = break_line(line)
                gene["species"] = tokens[1]
            elif line.startswith("OX"):
                tokens = break_line(line)
                gene["species_id"] = tokens[1]
            else:
                continue


class XMLParser(object):
    def __init__(self):
        self.tag_processors = {
            'name': XMLParser.get_name,
            'accession': XMLParser.get_accession,
            'protein': XMLParser.get_protein,
            'gene': XMLParser.get_gene,
            'organism': XMLParser.get_organism,
        }

    @staticmethod
    def get_name(tag, name_element, entry):
        entry['name'] = name_element.text

    @staticmethod
    def get_accession(tag, accession_element, entry):
        entry['accession'].append(accession_element.text)

    @staticmethod
    def get_protein(tag, protein_element, entry):
        for child in protein_element:
            child_tag = XMLParser.get_tag(child.tag)
            if child_tag == 'recommendedName':
                category = 'recommend'
            elif child_tag == 'alternativeName':
                category = 'alter'
            else:
                continue

            child_block = []
            for grandchild in child:
                grandchild_tag = XMLParser.get_tag(grandchild.tag)
                grandchild_text = grandchild.text
                if grandchild_tag == 'fullName':
                    grand_category = 'full'
                elif grandchild_tag == 'shortName':
                    grand_category = 'short'
                else:
                    continue

                if grandchild_text is None:
                    continue

                child_block.append((grand_category, grandchild.text))

            if category in entry['protein']:
                entry['protein'][category].append(child_block)
            else:
                entry['protein'][category] = [child_block]

    @staticmethod
    def get_gene(tag, gene_element, entry):
        for child in gene_element:
            entry['gene'].append((child.attrib['type'], child.text))

    @staticmethod
    def get_organism(tag, organism_element, entry):
        for child in organism_element:
            child_tag = XMLParser.get_tag(child.tag)

            if child_tag == 'name':
                if child.attrib['type'] == 'common':
                    entry['organism'].append(('organism_common', child.text))
                elif child.attrib['type'] == 'scientific':
                    entry['organism'].append(('organism_scientific', child.text))
                else:
                    continue
            elif child_tag == 'dbReference':
                if child.attrib['type'] == 'NCBI Taxonomy':
                    entry['organism'].append(('organism_ncbi_id', child.text))

    @staticmethod
    def get_new_entry():
        return {'name': None,
                'accession': [],
                'protein': {},
                'gene': [],
                'organism': []}

    @staticmethod
    def get_new_weibaike_entry():
        return {'uri': None,
                'name': [],
                'description': None,
                'properties': [],
                'links': {}}

    @staticmethod
    def get_weibaike_property(label, value):
        return {'label': label, 'value': value}

    @staticmethod
    def get_weibaike_entry(entry):
        """
        transfer an entry to the data structure for weibaike
        :param entry: an entry
        :type entry: dict
        :return: an weibaike entry
        :rtype: dict
        """
        wbk_entry = XMLParser.get_new_weibaike_entry()

        # uri set to uniprot url for the entry
        wbk_entry['uri'] = 'http://uniprot.org/uniprot/' + entry['accession'][0]

        # add entry name to name list and property dict
        wbk_entry['name'].append(entry['name'])
        wbk_entry['properties'].append(XMLParser.get_weibaike_property('name', entry['name']))

        # add all accessions to name list and property dict
        for accession in entry['accession']:
            wbk_entry['name'].append(accession)
            wbk_entry['properties'].append(XMLParser.get_weibaike_property('accession', accession))

        # add all recommended protein names to name list
        # connect recommended protein names as fullname|shortname|shortname|...
        # and set it as a property
        if 'recommend' in entry['protein']:
            for block in entry['protein']['recommend']:
                names = [b[1] for b in block]
                wbk_entry['name'] += names
                wbk_entry['properties'].append(XMLParser.get_weibaike_property('pro_rec',
                                                                               '|'.join(names)))
        # add all alternative protein names to name list
        # connect alternative protein names as fullname|shortname|shortname|...
        # and set it as a property
        if 'alter' in entry['protein']:
            for block in entry['protein']['alter']:
                names = [b[1] for b in block]
                wbk_entry['name'] += names
                wbk_entry['properties'].append(XMLParser.get_weibaike_property('pro_alt',
                                                                               '|'.join(names)))

        # add all gene names to name list
        # make a property gene_type for each gene name, e.g., gene_primary, gene_synonym
        for name in entry['gene']:
            wbk_entry['name'].append(name[1])
            prop_key = 'gene_' + name[0].lower()
            wbk_entry['properties'].append(XMLParser.get_weibaike_property(prop_key, name[1]))

        # add organism info into property dict
        for info_type, info in entry['organism']:
            if info_type == 'organism_common':
                wbk_entry['properties'].append(XMLParser.get_weibaike_property('org_com', info))
            elif info_type == 'organism_scientific':
                wbk_entry['properties'].append(XMLParser.get_weibaike_property('org_sci', info))
            elif info_type == 'organism_ncbi_id':
                wbk_entry['properties'].append(XMLParser.get_weibaike_property('org_ncbi', info))

        return wbk_entry

    @staticmethod
    def get_tag(uri_tag):
        # get the tag without uri
        # {http://uniprot.org/uniprot}name
        return uri_tag[uri_tag.find('}') + 1:]

    def parse(self, filepath):
        # get an iterable
        ElementTree.register_namespace('2', 'http://uniprot.org/uniprot')
        context = ElementTree.iterparse(filepath, events=("start", "end"))

        # turn it into an iterator
        context = iter(context)

        # get the root element
        event, root = next(context)

        for event, element in context:
            tag = self.get_tag(element.tag)
            if event == 'start' and tag == 'entry':
                entry = self.get_new_entry()
                for child in element:
                    tag = self.get_tag(child.tag)
                    if tag in self.tag_processors:
                        self.tag_processors[tag](tag, child, entry)

                if entry['name'] is None or entry['accession'] is None:
                    continue

                wbk_entry = XMLParser.get_weibaike_entry(entry)
                entry_json = json.dumps(wbk_entry)
                print(entry_json)

            if event == 'end' and tag == 'entry':
                # clear the root node to avoid too many empty elements
                root.clear()

if __name__ == '__main__':
    parser = XMLParser()
    parser.parse('data/uniprot_sprot.xml')