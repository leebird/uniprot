import sys
from lxml import etree
import json
from pprint import pprint
import gzip
import pickle


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
            'sequence': XMLParser.get_sequence,
            'keyword': XMLParser.get_keyword
        }

    @staticmethod
    def get_name(tag, name_element, entry):
        entry['name'] = name_element.text

    @staticmethod
    def get_accession(tag, accession_element, entry):
        entry['accession'].append(accession_element.text)

    @staticmethod
    def get_sequence(tag, element, entry):
        entry['sequence'] = element.text

    @staticmethod
    def get_keyword(tag, element, entry):
        entry['keyword'].append(element.text)

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

                if grandchild_text is None:
                    print(entry['name'], grandchild_tag, etree.tostring(child), file=sys.stderr)
                    continue

                if grandchild_tag == 'fullName':
                    grand_category = 'full'
                elif grandchild_tag == 'shortName':
                    grand_category = 'short'
                else:
                    continue

                if grandchild_text is None:
                    continue

                child_block.append((category, grand_category, grandchild.text))

            if category in entry['protein']:
                entry['protein'] += child_block
            else:
                entry['protein'] = child_block

    @staticmethod
    def get_gene(tag, gene_element, entry):
        for child in gene_element:

            if child.text is None:
                print(entry['name'], XMLParser.get_tag(child.tag), etree.tostring(child), file=sys.stderr)
                continue

            entry['gene'].append((child.attrib['type'], child.text))

    @staticmethod
    def get_organism(tag, organism_element, entry):
        for child in organism_element:
            child_tag = XMLParser.get_tag(child.tag)

            if child_tag == 'name':

                if child.text is None:
                    print(entry['name'], child_tag, etree.tostring(organism_element), file=sys.stderr)
                    continue

                if child.attrib['type'] == 'common':
                    entry['organism'].append(('organism_common', child.text))
                elif child.attrib['type'] == 'scientific':
                    entry['organism'].append(('organism_scientific', child.text))
                else:
                    continue
            elif child_tag == 'dbReference':
                if child.attrib['type'] == 'NCBI Taxonomy':
                    entry['organism'].append(('organism_ncbi_id', child.attrib['id']))

    @staticmethod
    def get_new_entry():
        return {
            'name': None,
            'accession': [],
            'protein': {},
            'gene': [],
            'organism': [],
            'keyword':[]
        }

    @staticmethod
    def get_new_weibaike_entry():
        return {
            'uri': None,
            'name': [],
            'description': None,
            'properties': [],
            'links': {}
        }

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
        if entry['name'] is not None:
            wbk_entry['name'].append(entry['name'])
            wbk_entry['properties'].append(XMLParser.get_weibaike_property('name', entry['name']))

        # add all accessions to name list and property dict
        for accession in entry['accession']:
            if accession is None:
                continue
            wbk_entry['name'].append(accession)
            wbk_entry['properties'].append(XMLParser.get_weibaike_property('accession', accession))

        # add all recommended protein names to name list
        # connect recommended protein names as fullname|shortname|shortname|...
        # and set it as a property
        if 'recommend' in entry['protein']:
            for block in entry['protein']['recommend']:
                names = [b[1] for b in block if b[1] is not None]
                wbk_entry['name'] += names
                wbk_entry['properties'].append(XMLParser.get_weibaike_property('pro_rec',
                                                                               '|'.join(names)))
        # add all alternative protein names to name list
        # connect alternative protein names as fullname|shortname|shortname|...
        # and set it as a property
        if 'alter' in entry['protein']:
            for block in entry['protein']['alter']:
                names = [b[1] for b in block if b[1] is not None]
                wbk_entry['name'] += names
                wbk_entry['properties'].append(XMLParser.get_weibaike_property('pro_alt',
                                                                               '|'.join(names)))

        # add all gene names to name list
        # make a property gene_type for each gene name, e.g., gene_primary, gene_synonym
        for name in entry['gene']:
            wbk_entry['name'].append(name[1])
            prop_key = 'gene_' + name[0].lower().replace(' ', '_')
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
        index = uri_tag.find('}')
        if index is None:
            print(uri_tag, file=sys.stderr)
            return uri_tag
        else:
            return uri_tag[index + 1:]

    def parse(self, filepath):
        # get an iterable
        context = etree.iterparse(gzip.GzipFile(filepath), 
                                  events=("end",), tag="{http://uniprot.org/uniprot}entry")

        for event, element in context:
            entry = self.get_new_entry()
            for child in element:
                tag = self.get_tag(child.tag)
                if tag in self.tag_processors:
                    self.tag_processors[tag](tag, child, entry)

            # if entry's name and uniprot ac is None, skip it
            if entry['name'] is None or entry['accession'] is None:
                continue

            #wbk_entry = XMLParser.get_weibaike_entry(entry)
            #entry_json = json.dumps(wbk_entry)
            #entry_json = json.dumps(entry)
            yield entry
            
            # clear element
            # http://stackoverflow.com/questions/12160418/why-is-lxml-etree-iterparse-eating-up-all-my-memory
            element.clear()


if __name__ == '__main__':
    xml_zip_file = sys.argv[1]
    parser = XMLParser()
    with open('ac_to_entrez.pk', 'rb') as f:
        ac_to_entrez = pickle.load(f)
    for entry in parser.parse(xml_zip_file):
        entrez = set()
        for ac in entry['accession']:
            if ac in ac_to_entrez:
                entrez |= ac_to_entrez[ac]
        entry['entrez'] = sorted(list(entrez))
        for kw in entry['keyword']:
            if 'kinase' in kw.lower():
                entry['kinase_in_keyword'] = True
                del entry['keyword']
                break
        entry_json = json.dumps(entry)
        print(entry_json)
    # parser.parse('data/test.xml')
    # parser.parse('data/14000_lines.xml')
