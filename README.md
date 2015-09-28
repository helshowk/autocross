# autocross

## Description

This is an automatic crossword puzzle generator written in python using ConceptNet and DbPedia.  The goal is to see if we can find interesting words to build a crossword given a seed subject word (e.g. 'nutrition', 'linux').

DISCLAIMER:  I realize these are nowhere near 'professional' crosswords especially because the layout is unconstrained but that was never the intention.

## Outline

There are three phases to the algorithm:

1. Select words for the crossword puzzle
2. Build the puzzle structure
3. Select hints

## Implementation

As it turns out each section is a bit tricky and get successively harder each step of the way.  The wordSource.py file is primarily responsible for collecting words using a very wide net (ConceptNet, DBPedia) and then pruning the word list using some natural language tools (nltk) to select verbs/nouns and a little random selections.

I recognize that the puzzle structure doesn't look like a real crossword puzzle.  To build the puzzle the code does almost an exhaustive search with some slight tricks to speed things up but this area could be improved significantly (multiprocessed, smarter word placements?).  The algorithm falls back on synonym sets if it can't find a fit for a given word.

Lastly, generating hints is really very difficult but down the road maybe a neural network reverse dictionary implementation would be fun to look into.  For now it falls through a progression of NYT database selections, synonyms, proverbs, and definitions.  Obviously would be great to eventually be able to train a neural network to produce clues but not there yet.

## Execution

Simply run 'python2.py puzzle.py PUZZLE_SEED'.  The output will be some json objects with clues, words, and positions.


