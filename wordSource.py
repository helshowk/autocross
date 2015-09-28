#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys, re
import urllib, urllib2, json
import operator
from SPARQLWrapper import SPARQLWrapper, JSON
import nltk
from nltk.corpus import stopwords
import enchant  # spell check
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.lancaster import LancasterStemmer
import numpy
from collections import defaultdict
from HTMLParser import HTMLParser
from random import shuffle

## constant definitions
DOCUMENT_DESCRIPTION = 0
DOCUMENT_DEFINITION = 1
DOCUMENT_NEWS = 2
DOCUMENT_URL = 3


## helper functions
def printSPARQL(results):
    if (results["head"].has_key("vars")):
        var_list = results["head"]["vars"]

        for r in results["results"]["bindings"]:
            for v in var_list:
                print str(v) + ": " + str(r[v]["value"].encode('utf8'))
    elif (results.has_key("boolean")):
        # answering an ASK
        print results["boolean"]


class Document():
    def __init__(self, t='', r='', docType=0, source=''):
        self.title = t
        self.raw = r
        self.docType = docType
        self.source = source

class Source():
    def __init__(self):
        self.documents = list()
        self.name = ''
    
    def __repr__(self):
        print str(name) + " has " + str(len(self.documents)) + " documents."
    
    def generateDocuments(self):
        return
        

class SourceHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.body = []
        self.title = ''
        self.curr_tag = ''
        self.in_body = False
        self.in_title = False
        
    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.in_title = True
            
        if tag == 'body':
            self.in_body = True
        self.curr_tag = tag
        
    def handle_endtag(self, tag):
        if tag == 'body':
            self.in_body = False
        if tag == 'title':
            self.in_title = False
        self.curr_tag = ''
        
    def handle_data(self, data):
        read_data = False
        if self.in_body and self.curr_tag <> 'script' and self.curr_tag <> 'style':
            read_data = True
        if read_data:
            if data.strip() <> '':
                self.body.append(data)
        if self.in_title:
            self.title = data
            
class HTMLSource(Source):
    # basic source single html document, strips out all tags and gets text from body of HTML only
    def __init__(self, url=''):
        Source.__init__(self)
        self.name = url
        self.url = url
        self.clear_internal_tags = True      # try to automatically remove link, span and other tags that may break up continuous text

    def generateDocuments(self):
        p = SourceHTMLParser()
        # in case it can't find a title
        p.title = self.name
        h = {
        'User-Agent': "IdylGames/0.1, (dev@idylgames.com)"
            }
                
        req = urllib2.Request(self.url, headers=h)
        cxn = urllib2.urlopen(req)
        for line in cxn.readlines():
            if self.clear_internal_tags:
                line = re.sub(r'<(a|b|span|i|small|strong)\s.*?>','',line)
                line = re.sub(r'</(a|b|span|i|small|strong)>','',line)

            p.feed(line)
    
        d = Document(p.title, '\n'.join(p.body), DOCUMENT_URL, self.url)
        return d
    

class DBPediaSource(Source):
    def __init__(self):
        Source.__init__(self)
        self.name = "DBPedia RDF"
        self.prefixes = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX : <http://dbpedia.org/resource/>
            PREFIX dbpedia2: <http://dbpedia.org/property/>
            PREFIX dbpedia: <http://dbpedia.org/>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dbo: <http://dbpedia.org/ontology/>
        """
        self.prefixes_lod = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX : <http://lod.openlinksw.com/resource/>
            PREFIX dbpedia2: <http://lod.openlinksw.com/property/>
            PREFIX dbpedia: <http://lod.openlinksw.com/>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dbo: <http://lod.openlinksw.com/ontology/>
        """
        self.endpoint = "http://live.dbpedia.org/sparql"
        self.endpoint_lod = "http://lod.openlinksw.com/sparql"
        self.sparql = SPARQLWrapper(self.endpoint)
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(500)
        self.links = list()
        self.topic_urls = list()
        self.visited = list()
        self.category_search = True
    
    def generateDocuments(self, term):
        if term in self.visited:
            return list()
            
        # pull down abstracts of all term concepts who belong to the category given by the term
        titles = list()
        docs = list()
        
        # basic query to get abstract for search term
        print "----- MAIN"
        sparql_cmd = self.prefixes + """
        SELECT ?title ?abstract ?topic
        WHERE {
          ?title rdfs:label "%s"@en .
          ?title <http://dbpedia.org/ontology/abstract> ?abstract .
          FILTER (langmatches(lang(?abstract), 'en')) .
          OPTIONAL {
            ?title foaf:isPrimaryTopicOf ?topic .
            }
        } LIMIT 50
        """ %(term)
        self.sparql.setQuery(sparql_cmd)
        
        try:
            results = self.sparql.query().convert()
            r = results["results"]["bindings"][0]
            title = term
            abstract = r["abstract"]["value"]
            titles.append(term)
            if abstract <> '':
                d = Document(term, abstract.encode('utf8'), DOCUMENT_DESCRIPTION, 'dbpedia')
                print "Added Definitions " + str(title)
                docs.append(d)
            topic_url = r["topic"]["value"]
            print "Added topic url " + str(topic_url)
            self.topic_urls.append(topic_url)
        except Exception, e:
            print "Error1: " + str(e)
            pass
        
        # add links
        print "----- LINKS"
        sparql_cmd = self.prefixes + """
        SELECT ?link
        WHERE {
            ?x rdfs:label "%s"@en .
             ?x <http://purl.org/dc/terms/subject> ?y .
             ?y rdfs:label ?link .   
        }
        """ %(term)
        self.sparql.setQuery(sparql_cmd)
        try:
            results = self.sparql.query().convert()
            for r in results["results"]["bindings"]:
                try:
                    link = r['link']['value'].encode('utf8')
                    if link not in self.links and (link <> term):
                        self.links.append(link)
                        print "Added link " + str(link)
                except Exception, e:
                    print "Error2: " + str(e)
                    continue
        except Exception, e:
            pass
        
        # search for concepts or categories that match the search term
        if self.category_search:
            print "----- CATEGORIES"
            sparql_cmd = self.prefixes + """
                SELECT ?title ?abstract 
                WHERE {
                    ?term_concept a skos:Concept .
                    ?term_concept rdfs:label "%s"@en .
                    ?s <http://purl.org/dc/terms/subject> ?term_concept .
                    OPTIONAL {
                        ?s dbo:abstract ?abstract . 
                    }
                    ?s rdfs:label ?title .
                    FILTER(langmatches(lang(?title), 'en')) .
                    FILTER(langmatches(lang(?abstract), 'en')) .
                }
            """ %(term)
            self.sparql.setQuery(sparql_cmd)
            
            try:
                results = self.sparql.query().convert()
                for r in results["results"]["bindings"]:
                    try:
                        if r['title']['value'].encode('utf8') not in titles:
                            title = r['title']['value'].encode('utf8')
                            abstract = r['abstract']['value'].encode('utf8')
                            if abstract <> '':
                                titles.append(title)
                                d = Document(title, abstract , DOCUMENT_DESCRIPTION, 'dbpedia')
                                self.links.append(title)
                                print "Added category " + str(title)
                                docs.append(d)
                    except Exception, e:
                        print "Error3: " + str(e)
                        continue
            except Exception,e:
                pass
        
        # pull down redirects if necessary
        print "----- REDIRECTS"
        sparql_cmd = self.prefixes + """
            SELECT ?redirectLabel ?redirectAbstract
            WHERE {
                ?title rdfs:label "%s"@en .
                ?title <http://dbpedia.org/ontology/wikiPageRedirects> ?redirectTo .
                ?redirectTo rdfs:label ?redirectLabel .
                ?redirectTo <http://dbpedia.org/ontology/abstract> ?redirectAbstract .
                FILTER (langMatches(lang(?redirectLabel), 'en')) .
                FILTER (langMatches(lang(?redirectAbstract), 'en')) .
            }
            """ %(term)
        self.sparql.setQuery(sparql_cmd)
        
        try:
            results = self.sparql.query().convert()
            print "Redirects: " + str(len(results["results"]["bindings"]))
            for r in results["results"]["bindings"]:
                try:
                    if r['redirectLabel']['value'].encode('utf8') not in titles:
                        title = r['redirectLabel']['value'].encode('utf8')
                        abstract = r['redirectAbstract']['value'].encode('utf8')
                        if abstract <> '':
                            titles.append(title)
                            d = Document(title, abstract , DOCUMENT_DESCRIPTION, 'dbpedia')
                            self.links.append(title)
                            print "Added document " + str(title)
                            docs.append(d)
                            
                    #if r['redirectLabel']['value'].encode('utf8') not in self.links:
                     #   self.links.append(r['redirectLabel']['value'].encode('utf8'))
                      #  print "Added redirect link to " + str(r['redirectLabel']['value'].encode('utf8'))
                except Exception, e:
                    print "Error4: " + str(e)
                    continue
        except Exception,e:
            pass
    
        self.visited.append(term)
        return docs

class FeedzillaSource(Source):
    def __init__(self):
        Source.__init__(self)
        self.name = "Feedzilla REST"
        self.article_search = "http://api.feedzilla.com/v1/articles/search.json?q="

    def generateDocuments(self, term):
        h = {'User-Agent': "IdylGames/0.1, (dev@idylgames.com)"}
        
        url = self.article_search + term
        req = urllib2.Request(url, headers=h)
        cxn = urllib2.urlopen(req)
        result = json.loads(cxn.read())
        processed = list()
        docs = list()
        try:
            for a in result["articles"]:
                source_url = a["url"]
                d = HTMLSource(source_url)
                doc = d.generateDocuments()
                title = doc.title
                raw = doc.raw
                print title
                print raw
                if title not in processed:
                    if raw <> '':
                        d = Document(title, raw, DOCUMENT_NEWS, 'feedzilla')
                        docs.append(d)
                        #print "Added url " + source_url + " title " + title + " and start data " + raw[0:100]
                        processed.append(title)
        except Exception,e:
            print e
            pass
        
        return docs

class WikipediaSource(Source):
    def __init__(self):
        Source.__init__(self)
        self.wiki_en_endpoint = "http://en.wikipedia.org/w/api.php"
        self.name = "MediaWiki API"
        self.links = list()
        self.sections = dict()
        
    def processWikiPage(self, data):
        refs = re.compile('<ref.*?>.*?</ref>', re.DOTALL)
        data = refs.sub('', data)
        
        files = re.compile('File:.*?px\|')
        data = files.sub('', data)
        
        links = list()
        temp = data
        for link in re.finditer('\[\[', data, re.M):
            start = link.span()[1]      # location of second [
            for i in range(start, len(data)-1):
                char = data[i]
                next_char = data[i+1]
                if  (char + next_char == ']]'):
                    lnk_text = data[start:i].split('|')
                    #links.append(lnk_text[0].replace(' ', '_'))
                    links.append(lnk_text[0])
                    if len(lnk_text) > 1:
                        # link and link text are different so replace content with link text
                        temp = temp.replace(data[start:i], lnk_text[1])
                    break
                
                if (char + next_char == '[['):
                    # bail, this is a nested loop which means we're looking somewhere not cool
                    break
        
        data = temp
        data = data.replace("{{", "")
        temp = data.replace("}}","")
        data = data.replace("[[","")
        data  = data.replace("]]","")
        
        return data, links    
    
    def generateDocuments(self, term, section=0):
        h = {
            'User-Agent': "IdylGames/0.1, (dev@idylgames.com)"
                }
        docs = list()
        try:
            # note rvsection = 0 means we're just getting the first section
            wiki_url = self.wiki_en_endpoint + "?action=query&titles=" + urllib.quote_plus(term) + "&prop=revisions&rvprop=content&format=json&rvsection=" + str(section)
            req = urllib2.Request(wiki_url, headers=h)
            cxn = urllib2.urlopen(req)
            result = json.loads(cxn.read())
            # now parse the result a bit to get links and top results
            current_rev_id = result['query']['pages'].keys()[0]
            data = result['query']['pages'][current_rev_id]['revisions'][0]['*']
            raw, links = self.processWikiPage(data)
            self.links = links
            title = term
            d = Document(title, raw, DOCUMENT_DEFINITION, 'wikipedia')
            docs.append(d)
        except Exception,e:
            print e
            
        return docs


class ConceptNetSource(Source):
    def __init__(self):
        Source.__init__(self)
        self.name = "ConceptNet REST"
        self.relations = ["CreatedBy", "HasContext", "HasProperty", "Causes", "AtLocation", "UsedFor", "CapableOf", "PartOf", "MemberOf", "IsA" ]
        #self.relations = [ "HasContext" ]
        self.search_endpoint = "http://conceptnet5.media.mit.edu/data/5.2/search?"
        self.assoc_endpoint = "http://conceptnet5.media.mit.edu/data/5.2/assoc?"
    
    def generateDocuments(self, term):
        h = {
        'User-Agent': "IdylGames/0.1, (dev@idylgames.com)"
            }
        docs = list()
        processed = list()
        try:
            for rel in self.relations:
                rel_arg = "/r/" + rel
                cn_url = self.search_endpoint + "text=" + urllib.quote_plus(term) + "&rel=" + rel_arg
                print cn_url
                req = urllib2.Request(cn_url, headers=h)
                cxn = urllib2.urlopen(req)
                result = json.loads(cxn.read())
                try:
                    for edge in result["edges"]:
                        temp = edge["startLemmas"]
                        temp = temp.split(' ')
                        title = temp[0].encode('utf8')
                        raw = ' '.join(temp[1:]).encode('utf8')
                        if title not in processed:
                            if raw <> '':
                                d = Document(title, raw, DOCUMENT_DEFINITION, 'conceptnet')
                                docs.append(d)
                                processed.append(title)
                except Exception,e:
                    print e
                    pass
        except Exception,e:
            print e
        
        return docs


class WordList():
    def __init__(self, search_term):
        search_term = sys.argv[1].lower()
        search_term = search_term[0].upper() + search_term[1:]
        self.search_term = search_term
    
    def build(self):
        print "Searching for: " + self.search_term
        docs = list()
        depth = 5   # max depths to check if documents haven't been found
        min_docs = 30
        max_docs = 100

        #feedzilla = FeedzillaSource()
        #print "generating feedzilla sources..."
        #docs = docs + feedzilla.generateDocuments(self.search_term)

        dbpedia = DBPediaSource()
        print "generating dbpedia sources..."
        
        try:
            docs = docs + dbpedia.generateDocuments(self.search_term)
        except urllib2.HTTPError:
            print "Fallback to LOD"
            # for now this overwrites but that's okay
            dbpedia.endpoint = dbpedia.endpoint_lod
            dbpedia.prefixes = dbpedia.prefixes_lod
            docs = dbpedia.generateDocuments(self.search_term)
    
        # DBPedia can also use:
        #       skos:broader

        # note it should present disambiguates back to user
        count = 0
        titles = [ d.title for d in docs ]
        # turn off category search after the first search
        dbpedia.category_search = False
        # the or will make sure we go down the rabbit hole once
        while ((count < depth) and (len(docs) < min_docs)) :
            print "Following step " + str(count+1)
            follow = dbpedia.links
            shuffle(follow)
            dbpedia.links = list()
            
            for link in follow:
                print "Following " + str(link)
                retVal = dbpedia.generateDocuments(link)
                for r in retVal:
                    if r.title not in titles:
                        docs.append(r)
                print "Documents: " + str(len(docs))
                titles = [ d.title for d in docs ]
                if len(docs) > max_docs:
                    break
            
            count = count + 1
            
        print "DBPedia docs: " + str(len(docs))

        # increase minimum documents
        min_docs = 50
        
        wikipedia = WikipediaSource()
        print "generating wikipedia sources..."
        try:
            docs = wikipedia.generateDocuments(self.search_term)
            
            count = 0
            titles = [ d.title for d in docs ]
            while ((count < depth) and (len(docs) < min_docs)):
                print "Following step " + str(count+1)
                follow = wikipedia.links
                shuffle(follow)
                wikipedia.links = list()
                print follow
                for link in follow:
                    print "Following " + str(link.encode('utf8'))
                    retVal = wikipedia.generateDocuments(link)
                    for r in retVal:
                        if r.title not in titles:
                            docs.append(r)
                    print "Documents: " + str(len(docs))
                    titles = [ d.title for d in docs ]
                    if len(docs) > max_docs:
                        break
                count = count + 1
        except urllib2.HTTPError:
            print "error with wikipedia, bailing on it"

        conceptnet = ConceptNetSource()
        print "generating conceptnet sources..."
        docs = docs + conceptnet.generateDocuments(self.search_term)

        print "Documents: " + str(len(docs))
        nouns = dict()
        verbs = dict()
        adjs = dict()
        titles = list()
        entities = list()

        lemm = WordNetLemmatizer()
        
        for d in docs:
            try:
                # entities for both title and raw
                #print "============================================================"
                #print "Title: \n" + d.title
                #print "Raw: \n" + d.raw
                #print "============================================================"
                
                ne_chunk = nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(d.title)), True)
                for n in ne_chunk.subtrees():
                    if n.label() == 'NE':
                        e = ' '.join([ x[0] for x in n.leaves() ])
                        entities.append(e)
                
                ne_chunk = nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(d.raw)), True)
                for n in ne_chunk.subtrees():
                    if n.label() == 'NE':
                        e = ' '.join([ x[0] for x in n.leaves() ])
                        entities.append(e)
                
                title_pos = d.title.encode("utf8").lower()
                raw_pos = d.raw.encode("utf8").lower()
                titles.append(title_pos)
                title_pos = nltk.pos_tag(nltk.word_tokenize(title_pos))
                raw_pos = nltk.pos_tag(nltk.word_tokenize(raw_pos))
                
                for w,t in title_pos:
                    if w in stopwords.words('english'):
                        pass
                    elif t.startswith('N'):
                        lemm_noun = lemm.lemmatize(w, 'n')
                        if not nouns.has_key(w):
                            nouns[w] = 0
                        nouns[w] += 1
                    elif t.startswith('V'):
                        inf_verb = lemm.lemmatize(w, 'v')
                        if not verbs.has_key(inf_verb):
                            verbs[inf_verb] = 0
                        verbs[inf_verb] += 1
                    elif t.startswith('J'):
                        
                        if not adjs.has_key(w):
                            adjs[w] = 0
                        adjs[w] += 1
                        
                for w,t in raw_pos:
                    if w in stopwords.words('english'):
                        pass
                    elif t.startswith('N'):
                        if not nouns.has_key(w):
                            nouns[w] = 0
                        nouns[w] += 1
                    elif t.startswith('V'):
                        inf_verb = lemm.lemmatize(w, 'v')
                        if not verbs.has_key(inf_verb):
                            verbs[inf_verb] = 0
                        verbs[inf_verb] += 1
                    elif t.startswith('J'):
                        if not adjs.has_key(w):
                            adjs[w] = 0
                        adjs[w] += 1
                        
            except Exception,e:
                print e
                pass

        # do a frequency count first
        sorted_nouns = sorted(nouns.items(), key = operator.itemgetter(1))
        sorted_verbs = sorted(verbs.items(), key = operator.itemgetter(1))
        sorted_adjs = sorted(adjs.items(), key = operator.itemgetter(1))

        final_words = list()

        def prob_sort_words(word_list):
            #prob_sorted = [ (w, 1./f) for w,f in word_list if f <> 1 ]
            prob_sorted = [ (w, 1./(numpy.log(1+f))) for w,f in word_list if f <> 1 ]
            total = sum([ x[1] for x in prob_sorted ])
            prob_sorted = [ (w, float(inv_f/total)) for w,inv_f in prob_sorted ]
            return prob_sorted
        
        n = prob_sort_words(sorted_nouns)
        final_words = final_words + list(numpy.random.choice([ x[0] for x in n ], size=(len(n)/3), p=[ x[1] for x in n ], replace=False))

        v = prob_sort_words(sorted_verbs)
        final_words = final_words + list(numpy.random.choice([ x[0] for x in v ], size=(len(v)/3), p=[ x[1] for x in v ], replace=False))

        j = prob_sort_words(sorted_adjs)
        final_words = final_words + list(numpy.random.choice([ x[0] for x in j ], size=(len(j)/3), p=[ x[1] for x in j ], replace=False))

        entities = list(set(entities))
        if len(titles) > 0:
            final_words = final_words + list(numpy.random.choice(titles, size=(len(titles)/4)))
        if len(entities) > 0:
            final_words = final_words + list(numpy.random.choice(entities, size=(len(entities)/6)))

        # drop all multi-word entries:  better later to split them
        final_words = [ f.lower() for f in final_words if len(nltk.word_tokenize(f)) == 1 ]

        # read ANC word frequency distribution
        fin = open('anc-freq-lemma.txt', 'r')
        raw_freq = fin.readlines()
        fin.close()

        frequencies = defaultdict(float)
        total = 0
        for line in raw_freq:
            tokens = line.split('\t')
            if (len(tokens) == 4):
                w = tokens[0]
                frequencies[w] += float(tokens[3])
                total += float(tokens[3])

        for k,v in frequencies.items():
            frequencies[k] /= total

        # drop words with zero frequency
        final_filter = [ (w, frequencies[w]) for w in list(set(final_words)) if frequencies[w] <> 0 ]
        final_filter = prob_sort_words(final_filter)
        final_words = list(numpy.random.choice([ x[0] for x in final_filter ], size=len(final_filter), p=[ x[1] for x in final_filter ], replace=False))

        # now remove words we know we don't want in there but might get in:
        #   wikipedia
        final_words = list(set(final_words))
        remove_words = [ 'wikipedia' ]
        final_words = [ w for w in final_words if w not in remove_words ]

        # remove duplicate stems
        st = LancasterStemmer()
        stemmed_words = list()
        temp = list()
        for w in final_words:
            stem = st.stem(w)
            if stem not in stemmed_words:
                stemmed_words.append(stem)
                # arbitrarily take the first word which matches the stem, ignore the others
                temp.append(w)
        
        final_words = temp

        return final_words



if __name__ == "__main__":
    if len(sys.argv) < 1:
        print "Usage: wordSource.py <search_term>"
        sys.exit()

    search_term = sys.argv[1].lower()
    search_term = search_term[0].upper() + search_term[1:]
    test = WordList(search_term)
    print test.build()
    

# word source algorithm
#   use seed word to get terms from different sources:
#       - dbpedia
#       - ConceptNet:
#           - parse return nodes by /c/en/<title>/n/<raw>
#           - rels: 
#               - /r/CreatedBy (B created by A)
#               - /r/HasContext (B has context A)
#               - /r/HasProperty (A has B as a property)
#               - /r/Causes (A and B are events and it's typical for A to cause B)
#               - /r/AtLocation (A is the typical or inherent location of B)
#               - /r/UsedFor (A is the typical or inherent location of B)
#               - /r/CapableOf (Something that A can do is typically B)
#               - /r/PartOf (A is part of B)
#               - /r/MemberOf (A is member of B, B is a group that contains A)
#               - /r/IsA (A is a subtype or specific instance of B)
#           - also use http://conceptnet5.media.mit.edu/data/5.2/assoc/list/en/toast,cereal,juice,egg to build lists of terms that might be relevant
#
#   Note that later on we can use conceptnet for definitions and for generating hints!
#
#   Should expand source of documents to include:
#       - wikimedia API full page of content for a single word if it exists
#       - news APIs
