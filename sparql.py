#!/usr/bin/env python2

from SPARQLWrapper import SPARQLWrapper, JSON

def printSPARQL(results):
    if (results["head"].has_key("vars")):
        var_list = results["head"]["vars"]

        for r in results["results"]["bindings"]:
            for v in var_list:
                print str(v) + ": " + str(r[v]["value"].encode('utf8'))
    elif (results.has_key("boolean")):
        # answering an ASK
        print results["boolean"]


sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql.setQuery("""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX type: <http://dbpedia.org/class/yago/>
    PREFIX prop: <http://dbpedia.org/property/>
    SELECT DISTINCT ?country_name ?population
    FROM <http://dbpedia.org>
    WHERE
        {
            ?country rdf:type type:LandlockedCountries ;
                            rdfs:label ?country_name ;
                            prop:populationEstimate ?population .
                    FILTER (?population > 15000000 && langMatches(lang(?country_name), "EN")) .
        } 
        """)
sparql.setReturnFormat(JSON)
#results = sparql.query().convert()
    

sparql = SPARQLWrapper("http://drugbank.bio2rdf.org/sparql")
sparql.setQuery("""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX db: <http://bio2rdf.org/drugbank_vocabulary:>
    SELECT ?drug_name ?dosage ?indication
    WHERE {
        ?drug a db:Drug .
        ?drug rdfs:label ?drug_name .
        OPTIONAL 
            {
            ?drug db:dosage ?do . 
            ?do rdfs:label ?dosage .
            }
        OPTIONAL 
            {
            ?drug db:indication ?ind . 
            ?ind rdfs:label ?indication
            }
        } LIMIT 10
        """)
sparql.setReturnFormat(JSON)
#results = sparql.query().convert()


sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql.setQuery("""
    PREFIX prop: <http://dbpedia.org/property/>
    ASK {
        <http://dbpedia.org/resource/Amazon_River> prop:length ?amazon .
        <http://dbpedia.org/resource/Nile> prop:length ?nile .
        FILTER ( ?amazon > ?nile)
        }
    """)
sparql.setReturnFormat(JSON)
#results = sparql.query().convert()


sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql.setQuery("""
    PREFIX dbpr: <http://dbpedia.org/resource/>
    PREFIX dbpo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?abstract
    WHERE {
        ?s rdfs:label "boxing"@en .
        ?s dbpo:abstract ?abstract .
    }
    """)
sparql.setReturnFormat(JSON)
results = sparql.query().convert()

#printSPARQL(results)


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

# select everything from dbpedia which has 'boxing' in it's label
SELECT ?s ?o
WHERE {
  ?s rdfs:label ?o 
  FILTER regex (?o, ".* boxing .*")
} LIMIT 100

# select all subjects that have boxing as a category
SELECT ?s
WHERE {
?term_concept a skos:Concept .
?term_concept rdfs:label ?concept_label .
?s <http://purl.org/dc/terms/subject> ?term_concept
}

# select abstracts of all subjects that have boxing as a category
PREFIX dbo: <http://dbpedia.org/ontology/>
SELECT ?s ?abstract
WHERE {
 ?term_concept a skos:Concept .
 ?term_concept rdfs:label "Boxing"@en .
 ?s <http://purl.org/dc/terms/subject> ?term_concept .
 ?s dbo:abstract ?abstract
 FILTER (langMatches(lang(?abstract), 'en'))
} LIMIT 50
