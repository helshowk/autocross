#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys, time
import csv
import numpy
import string, re
import operator
import urllib2, json
from collections import defaultdict, namedtuple
from nltk.corpus import wordnet
import wordSource

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.lancaster import LancasterStemmer

def buildPuzzle(search_term):
    board_size = 15
    max_word_length = 10
    min_word_length = 3
    p = Puzzle(dictionary=list(), x=board_size, y=board_size)
    wordsource = wordSource.WordList(search_term)
    words = wordsource.build()
    # remove words that have the same stem    
    words = [ w for w in words if len(w) <= max_word_length and len(w) >= min_word_length ]
    # remove words that don't have hints
    hints = p.generateHints(words)
    words = hints.keys()
    p.dictionary = words
    print "Word pool: " + str(len(words))
    
    avg_length = numpy.average([ len(w) for w in words ])
    puzzle_words = min(len(words), int((board_size*board_size)*(1/avg_length)*0.7))
    print "Building puzzle of size " + str(puzzle_words)
    wm, matches =  p.confirmWords(words)

    # now maybe do something with wm using only the highest # of overlaps?
    for i in wm.keys():
        if wm[i] == 0:
            print "removing " + str(i)
            del(wm[i])
            
    if len(wm) < 10:
        print "Not enough words!"

    final_words = wm.keys()
    #word_lengths = numpy.array([ len(w) for w in final_words ])
    #prob_lengths = numpy.array([ (max_word_length/2 - abs(l-avg_length) / std_length) for l in word_lengths ])
    #s = numpy.sum(prob_lengths)
    #prob_lengths /= s
    #print final_words
    #final_words = numpy.random.choice(final_words, size=puzzle_words, replace=False, p = prob_lengths)

    #print "selected words: "
    #print final_words

    selected_words = list()
    num_words = 0
    while num_words < puzzle_words:
       selected_words = p.buildPuzzle(final_words, matches, hints)
       num_words = len(selected_words)
       print p
       
       if num_words >= puzzle_words:
            # confirm puzzle has no stranded words
            row_idx = 0
            col_idx = 0
            rows = p.grid.shape[0]
            cols = p.grid.shape[1]
            
            # check for stranded rows
            for row in p.grid[...,:]:
                next_row = None
                prev_row = None
                if row_idx < (rows-1):
                    next_row = p.grid[row_idx+1, :]
                    
                if row_idx > 0:
                    prev_row = p.grid[row_idx-1, :]
                
                idx_start = -1
                idx_end = len(row)
                stranded = False
                for idx,e in enumerate(row):
                    if e <> 0:
                        if idx_start == -1:
                            idx_start = idx
                            stranded = True
                        
                        if prev_row is not None:
                            if prev_row[idx] <> 0:
                                stranded = False
                                
                        if next_row is not None:
                            if next_row[idx] <> 0:
                                stranded = False
                    else:
                        if stranded: 
                            idx_end = idx
                            p.grid[row_idx,idx_start:idx_end] = 0
                            num_words -= 1
                        idx_start = -1
                
                # check final part of row            
                if stranded:
                    p.grid[row_idx, idx_start:idx_end] = 0
                    num_words -= 1
                    
                row_idx += 1
                
            # check for stranded cols
            for col in p.grid.T[..., :]:
                next_col = None
                prev_col = None
                if col_idx < (cols-1):
                    next_col = p.grid.T[col_idx+1, :]
                if col_idx > 0:
                    prev_col = p.grid.T[col_idx-1, :]
                
                stranded = False
                idx_start = -1
                idx_end = len(col)
                for idx,e in enumerate(col):
                    if e <> 0:
                        if idx_start == -1: 
                            idx_start = idx
                            stranded = True
                            
                        if prev_col is not None:
                            if prev_col[idx] <> 0:
                                stranded = False
                        if next_col is not None:
                            if next_col[idx] <> 0:
                                stranded = False
                    else:
                        if stranded:
                            idx_end = idx
                            p.grid[idx_start:idx_end,col_idx] = 0
                            num_words -= 1
                        idx_start = -1
                        
                if stranded:
                    p.grid[ idx_start:idx_end , col_idx] = 0
                    num_words -= 1
                
                col_idx += 1
    
    print "FINAL:" + str(puzzle_words)
    print p
    print p.down_words
    print p.across_words
    print hints
    print p.hiddenWordBoard()
    print p.javascriptOutput()
    return p, hints


class Puzzle:
    def __init__(self, dictionary, x=20, y=20, name=''):
        self.x = x
        self.y = y
        self.name = name
        self.valid_words = dictionary
        self.grid = numpy.zeros((self.x, self.y))
        self.down_words = dict()
        self.across_words = dict()
    
    def clearPuzzle(self):
        self.grid = numpy.zeros((self.x, self.y))
        self.down_words = dict()
        self.across_words = dict()
    
    def __repr__(self):
        result = list()
        result.append("Puzzle: " + self.name)
        result.append("  " + "---"*self.x)
        for i in range(0,self.x):
            row = ' |'
            for j in range(0, self.y):
                ascii_code = int(self.grid[i][j])
                if ascii_code <> 0:
                    row = row + "  " + chr(ascii_code)
                else:
                    row = row + "  " + " "
                    
            row = row + " |"
            result.append(row)
            
        result.append("  " + "---"*self.x)
        return '\n'.join(result)
    
    def hiddenWordBoard(self):
        result = list()
        result.append("Puzzle: " + self.name)
        result.append("  " + "---"*self.x)
        for i in range(0,self.x):
            row = '|'
            for j in range(0, self.y):
                ascii_code = int(self.grid[i][j])
                if ascii_code <> 0:
                    row = row + "  " + "X"
                else:
                    row = row + "  " + " "
                    
            row = row + " |"
            result.append(row)

        result.append("  " + "---"*self.x)
        return '\n'.join(result)
    
    def javascriptOutput(self):
        js_out = list()
        js_out.append("var puzzle = new Array();")
        for pos,word_hint in self.down_words.items():
            x_pos = pos[0]
            y_pos = pos[1]
            word = word_hint[0]
            hint = word_hint[1]
            js_out.append("puzzle.push({ x: " + str(x_pos) + ", y: " + str(y_pos) + ", word: '" + word + "', dir: 'down', hint: '" + hint + "'});")
        
        for pos,word_hint in self.across_words.items():
            x_pos = pos[0]
            y_pos = pos[1]
            word = word_hint[0]
            hint = word_hint[1]
            js_out.append("puzzle.push({ x: " + str(x_pos) + ", y: " + str(y_pos) + ", word: '" + word + "', dir: 'across', hint: '" + hint + "'});")
                
        return '  '.join(js_out)
    
    def confirmWords(self, words):
        # confirm all words can in the set can be arranged with overlapping letters without
        # using the same position twice
        
        # very weak confirmation: all words in the set match with at least one letter
        # stronger confirmation: all words in the set match with at least one letter and no letter is used twice to match up         
        matches = defaultdict(list)
        length = len(words)
        for idx in range(0,length):
            # loop through all other words
            for idx2 in range(0,length):
                w1 = words[idx]
                w2 = words[idx2]
                if w1 <> w2:
                    # for each character
                    ords = list()
                    for l_idx,l in enumerate(w1):
                        ords += [ (l_idx, i) for i,x in enumerate(w2) if ord(x) == ord(l) ]
                        
                    matches[w1].append((w2, ords))
    
        # note that matches has double entires i.e. matches[w1] = (w2, ords) and a matches[w2] = (w1, ords)
        word_matches = defaultdict(int)
        for k,v in matches.items():
            for match in v:
                # match is an element of the list and is tuple (word, ordinals) where ordinals is a list of matching character positions
                word_matches[k] += len(match[1])
        
        return word_matches, matches

    def wordSynSets(self, words, max_length, replace_space=''):
        # build synsets of words:
        syns = list()
        
        for w in words:
            synsets = wordnet.synsets(w)
            if len(synsets) > 1:
                for s in synsets:
                    syns = syns + [ l.name().replace('_',replace_space) for l in wordnet.synset(s.name()).lemmas() if len(l.name().replace('_',replace_space)) < max_length ]
        
        syns = list(set(syns))
        return syns

    def buildPuzzle(self, words_in, matches, hints):
        # build a puzzle out of the words
        # clear puzzle
        self.clearPuzzle()
        
        # start off placing the first word in the top left of the board
        words = words_in
        max_pool_size = 500
        if len(words) > max_pool_size:
            words = numpy.random.choice(words,size=max_pool_size, replace=False)
        
        weight_matrix = numpy.zeros((self.x, self.y))
        max_weight = 1.25
        min_weight = 1
        mid_x = (self.x-1) / 2.
        mid_y = (self.y-1) / 2.
        
        for i in range(0,self.x):
            for j in range(0, self.y):
                temp = numpy.power(mid_x - i,2) + numpy.power(mid_y - j,2)
                temp /= numpy.power(mid_x,2) + numpy.power(mid_y,2)
                temp = 1-temp
                temp = temp * (max_weight - min_weight) + min_weight
                weight_matrix[i][j] = temp + numpy.random.normal(0,0.05)
        
        #weight_matrix = numpy.ones((self.x, self.y))
        
        numpy.random.shuffle(words)
        word_lengths = numpy.array([ len(w) for w in words ])
        max_length = numpy.max(word_lengths)
        avg_length = numpy.average(word_lengths)
        std_length = numpy.std(word_lengths)
        
        selected_words = list()
        syns = self.wordSynSets(words, max_length)
        # confirm stems?
        # also maybe rebuild syns at each failed placement so we don't use synonyms of words that have already been place i.e. you can exclude selected_words from the syn search
        
        print "Syns length: " + str(len(syns))
        self.valid_words += syns
        times = list()
        
        #for n in range(0,int(puzzle_words*2)):
        for n in range(0,1000):
            t0 = time.time()
            selected_words.append('')
            
            if (n % 2 == 0):
                direction = 0
            else:
                direction = 1
                
            print "Placing word " + str(n)
            print self
            
            # to speed up checks
            self.row_sums = dict()
            self.col_sums = dict()
            for idx,r in enumerate(self.grid):
                self.row_sums[idx] = numpy.sum(r == 0)
            
            for idx,c in enumerate(self.grid.T):
                self.col_sums[idx] = numpy.sum(c == 0)
                
                
            #min_wrd_length = numpy.random.choice(range(2,5),1)
            random_draw = numpy.random.normal(avg_length, std_length, 1)[0]-1
            min_wrd_length = min(max_length * 0.6, random_draw-1)
            min_wrd_length = round(min_wrd_length, 0)
            min_wrd_length = numpy.random.choice([2, 3, 4])
            if (n > len(words)/3):
                min_word_length = 0
            
            if (n == 0):
                w = numpy.random.choice(words, size=1)[0]
                selected_words[0] = str(w)
                word_direction = defaultdict(int)
            else:
                sums = numpy.inf * numpy.ones((self.x, self.y))
                word_positions = defaultdict(str)
                word_direction = defaultdict(int)
                
                def _check_all_words(word_pool, direction, hints, debug=False, syns=False):       
                    print len(word_pool)
                    options = 0
                    for idx,w in enumerate(word_pool):
                        # maybe include an early stop i.e. after seeing 5 or 10 valid options?                    
                        if options < 30:
                            if len(w) > min_wrd_length and (w not in selected_words):
                                for i in range(0,self.x):
                                    if (direction == 1):
                                        if self.row_sums[i] < len(w):
                                            continue
                                    
                                    placed = False
                                    for j in range(0, self.y):
                                        if debug:
                                            print idx, i, j
                                        
                                        if (direction == 0):
                                            if self.col_sums[i] < len(w):
                                                continue
                                                
                                        try:
                                            possible_grid = self.addWord(w, (i,j), direction)
                                            overlap_pts = numpy.sum(possible_grid > 0)
                                            if sums[i][j] > overlap_pts:
                                                sums[i][j] = overlap_pts
                                                if syns:
                                                    if not hints.has_key(w):
                                                        # try to find a hint
                                                        single_hint = self.generateHints([w])
                                                        if single_hint.has_key(w):
                                                            hints[w] = single_hint[w]
                                                    
                                                    # make sure you don't add any words without hints
                                                    if hints.has_key(w):
                                                        word_positions[(i,j)] = w
                                                        word_direction[(i,j)] = direction
                                                        placed = True
                                                else:
                                                    word_positions[(i,j)] = w
                                                    word_direction[(i,j)] = direction
                                                    placed = True
                                        except Exception,e:
                                            if debug:
                                                print e
                                            pass
                                    if placed:
                                        options += 1
                                        
                _check_all_words(words, direction, hints)
                
                if numpy.sum(numpy.isfinite(sums)) == 0:
                    print "Checking synonyms"
                    _check_all_words(syns, direction, hints, syns=True)
                    
                if numpy.sum(numpy.isfinite(sums)) == 0:
                    print "Checking other direction"
                    new_direction = not(direction or 0)  # flip direcitons and try words and syns again
                    _check_all_words(words, new_direction, hints, syns=True)
                    
                if numpy.sum(numpy.isfinite(sums)) == 0:
                    print "Checking syns in other direction"
                    _check_all_words(syns, new_direction, hints, syns=True)
                        
                if numpy.sum(numpy.isfinite(sums)) == 0:
                    print "nowhere to place the next word!"
                    return selected_words

                   
            # find the minimum values in sums using == min() and then using nonzero() to extract a tuple of arrays with index values
            # the return value of nonzero() are arrays with indices for each dimension (i.e. array1 is for index1, array2 is for index2 etc..)
            # so we then need to zip up those elements to get tuples of actual indices, i.e. (x,y) for x,y in zip(....)
            # then just choose randomly from that list of allowed values
            if n <> 0:
                # use the weight matrix to discourage placing inside the puzzle immediately
                sums = sums * weight_matrix
                positions = (sums == sums.min()).nonzero()
                positions = [ (x,y) for x,y in zip(positions[0],positions[1]) ]
                numpy.random.shuffle(positions)
                pos = positions[0]
                selected_words[n] = word_positions[pos]
            else:
                pos = (numpy.random.choice(self.x-len(selected_words[n])-1,1)[0], numpy.random.choice(self.y-len(selected_words[n])-1,1)[0])
                word_direction[pos] = int(round(numpy.random.rand(1)))
            
            word_flag = 0
            try:
                self.grid = self.addWord(selected_words[n], pos, word_direction[pos])
                if word_direction[pos] == 0:
                    self.down_words[pos] = (selected_words[n], hints[selected_words[n]])
                elif word_direction[pos] == 1:
                    self.across_words[pos] = (selected_words[n], hints[selected_words[n]])
            except Exception, e:
                print selected_words[n], pos, word_direction[pos], hints[selected_words[n]]
                selected_words[n] = ''
                word_direction[pos] = 0
                print e
            times.append(time.time() - t0)
            print "That took " + str(round(time.time() - t0, 4)) + " seconds"
        
        print "Average time: " + str(numpy.average(numpy.array(times)))
        print "Total time: " + str(numpy.sum(numpy.array(times)))
        return selected_words
    
    def addWord(self, w, position, direction):
        # w is the word
        # position is a tuple indexing the grid position starting at 0,0 in the top left corner
        # direction is 0 for down, 1 for across
        #
        # returns '' if everything is okay, otherwise raises exception GridNotEmpty, WordDoesntExist, WordTooLarge
        
        w_length = len(w)
        idx00 = position[0]
        idx01 = position[1]
        
        if (direction == 0):
            idx10 = idx00 + w_length
            idx11 = idx01
        elif (direction == 1):
            idx10 = idx00
            idx11 = idx01 + w_length
        
        if (idx11 > self.y) or (idx10 > self.x):
            raise Exception("WordTooLarge")
        
        # check if grid has a word going in the same direction
        if direction == 0:
            if self.down_words.has_key((idx00,idx01)):
                #print "word exists going down: " + str(self.down_words[(idx00,idx01)])
                raise Exception("GridNotEmpty")
        elif direction == 1:
            if self.across_words.has_key((idx00,idx01)):
                #print "word exists going across: " + str(self.across_words[(idx00,idx01)])
                raise Exception("GridNotEmpty")
                
        return_grid = self.grid.copy()
        
        hcnt = 0
        vcnt = 0
        for c in w:
            if (return_grid[hcnt+idx00][vcnt+idx01] <> 0) and (return_grid[hcnt+idx00][vcnt+idx01] <> ord(c)):
                raise Exception("GridNotEmpty")
            
            #if ((hcnt > 1) or (vcnt > 1)) and (return_grid[hcnt+idx00][vcnt+idx01] <> 0):
                #raise Exception("GridNotEmpty")
            
            return_grid[hcnt+idx00][vcnt+idx01] = ord(c)
            if (direction == 0):
                hcnt += 1
            elif (direction == 1):
                vcnt += 1

        # now check that all words that can be created are valid words
        for row in return_grid[...,:]:
            temp = [ chr(int(n)) if n <> 0 else ' ' for n in row ]
            words = ''.join(temp).strip().split(' ')
            for wrd in words:
                if len(wrd) > 1:
                    if wrd not in self.valid_words:
                        raise Exception("WordDoesntExist")
        
        for col in return_grid.T[..., :]:
            temp = [ chr(int(n)) if n <> 0 else ' ' for n in col]
            words = ''.join(temp).strip().split(' ')            
            for wrd in words:
                if len(wrd) > 1:
                    if wrd not in self.valid_words:
                        raise Exception("WordDoesntExist")
        
        return return_grid

    def conceptNetIsA(self,w):
        w = w.encode('utf8')
        h = {
        'User-Agent': "IdylGames/0.1, (dev@idylgames.com)"
            }
        
        rels = [ "IsA" ]
        for r in rels:
            cn_url = "http://conceptnet5.media.mit.edu/data/5.2/search?text=" + w + "&rel=/r/IsA"
            #print cn_url
            req = urllib2.Request(cn_url, headers=h)
            cxn = urllib2.urlopen(req)
            result = json.loads(cxn.read())
            retVal = list()
            
            for edge in result["edges"]:
                temp = edge["endLemmas"]
                temp = temp.split(' ')
                title = temp[0].encode('utf8')
                raw = ' '.join(temp[1:]).encode('utf8')
                raw = raw.replace(w, '')
                if (title == w) and (raw not in retVal):
                    retVal.append(raw)
                
        return retVal

    def generateHints(self, words):
        # given a list of words, create a dictionary of clues keyed by the words
        # progression:
        #   - search NYT database for possible clues
        #   - use synonyms from wordnet
        #   - use definitions
        #   - use common proverbs or phrases
        #   - use conceptNet
        #   - use dbpedia
        
        fin = open('proverbs','r')
        data =fin.readlines()
        fin.close()
        proverbs = [ l.rstrip('\n') for l in data if l <> '' ]
        
        nyt_clues = defaultdict(list)
        with open('clues.txt', 'rU') as fin:
            for line in fin:
                temp = line.split('\t')
                nyt_clues[temp[1]].append(temp[0])
        
        
        # should later also use docset from wordsource somehow
        hints = defaultdict(list)
        for w in words:
            print "generating hints for " + w + "..."
            if nyt_clues.has_key(w.upper()):
                print "NYT clue"
                hints[w] += [ ('NYT', nyt_clues[w]) ]
            
            synsets = wordnet.synsets(w)
            if len(synsets) > 0:
                definition = synsets[0].definition()
                #print "def: " + str(definition)
                def_re = re.compile(' ' + w + ' ', re.IGNORECASE)
                hints[w] += [ ('DEF', def_re.sub(' ' + '_'*len(w) + ' ',  definition)) ]
                #examples = synsets[0].examples()
                #hints[w] += [ ('EX', s.replace(w, ' ' + '_'*len(w) + ' ')) for s in examples if s.find(' '+ w + ' ') <> -1 ]
            
            syns = self.wordSynSets([w],100, ' ')
            hints[w] += [ ('SYN', s) for s in syns if s.lower() <> w.lower() ]
            hints[w] += [ ('PRV', s.replace(w, '_'*len(w))) for s in proverbs if s.find(' '+ w + ' ') <> -1 ]
            
            #if len(hints[w]) == 0:
                #concept_net_hints = self.conceptNetIsA(w)
                ##print concept_net_hints
                #hints[w] += [ ('CON', h.replace(' ' + w + ' ', '')) for h in self.conceptNetIsA(w) ]
            #print w + ":"
            #print "----------------------"
            #print hints[w]
            #print "----------------------"
        
        final_hints = dict()
        hint_type_cnt = dict()
        #hint_type_cnt['EX'] = 0
        hint_type_cnt['NYT'] = 0
        hint_type_cnt['PRV'] = 0
        hint_type_cnt['SYN'] = 0
        hint_type_cnt['DEF'] = 0
        hint_type_cnt['CON'] = 0
        
        for k,v in hints.items():
            print "selecting hint for " + str(k) + "..."
            # if there's a NYT list then randomly select from that
            nyt_hints = [ x for x in v if x[0] == 'NYT' ]
            if (len(nyt_hints) > 0):
                final_hints[k] = numpy.random.choice(nyt_hints[k])
                print "nyt hint: " + final_hints[k]
            else:
                if len(v) == 0:
                    # don't include this word in the returned dictionary
                    pass
                elif len(v) == 1:
                    final_hints[k] = v[0][1]
                    hint_type_cnt[v[0][0]] += 1
                else:
                    # randomly select hint types but preference is to keep the mix even
                    fail = True
                    cnt = 0
                    while fail and cnt < len(v):
                        cnt += 1
                        current_hint_types = [ h[0] for h in v ]
                        hint_probabilities = [ (hc_k, 1./(hc_v+1)) for hc_k,hc_v in hint_type_cnt.items() if hc_k in current_hint_types ]
                        if len(hint_probabilities) == 0:
                            hint_idx = numpy.random.choice(range(0,len(v)))
                            hint = v[hint_idx]
                            hint_type_cnt[hint[0]] += 1
                            final_hints[k] = hint[1]
                            fail = False
                        else:
                            normalizing_factor = numpy.sum([ x[1] for x in hint_probabilities ])
                            hint_probabilities = [ (x[0], float(x[1]) / float(normalizing_factor)) for x in hint_probabilities ]
                            hint_type = numpy.random.choice([ x[0] for x in hint_probabilities ], size=1, p=[ x[1] for x in hint_probabilities ])
                            hint_type = hint_type[0]
                            
                            if ((hint_type == 'SYN') or (hint_type == 'CON') or (hint_type == 'PRV')):
                                # randomly select a synonym
                                all_hints = [ h for h in v if h[0] == hint_type ]
                                hint_idx = numpy.random.choice(range(0,len(all_hints)))
                                hint = all_hints[hint_idx]
                                if (self.searchString(hint[1], k)):
                                    final_hints[k] = hint[1]
                                    hint_type_cnt[hint_type] += 1
                                    fail = False
                            elif (hint_type == 'DEF'):
                                defs = [ h for h in v if h[0] == 'DEF' ]
                                for d in defs:
                                    if d[1].find('_') == -1:
                                        final_hints[k] = d[1]
                                        fail = False
                                        hint_type_cnt[hint_type] += 1
                                        break
                                
        return final_hints
        
    def searchString(self, sentence, search_word):
        # search sentence for given word, lemmatize everything
        lemm = WordNetLemmatizer()
        lem_search = lemm.lemmatize(search_word)
        for idx,word in enumerate(sentence.split(' ')):
            if lemm.lemmatize(word).lower() == lem_search.lower():
                return idx
            else:
                return -1

if __name__ == "__main__":
    search_term = sys.argv[1].lower()
    search_term = search_term[0].upper() + search_term[1:]
    puz = buildPuzzle(search_term)
    #words = [u'criticism', u'opinions', u'examines', u'leaders', u'sentence', u'electoral', u'energy', u'citation', u'results', u'logical', u'potemkin', u'professor', u'commute', u'puppet', u'communist', u'consists', u'crime', u'sexual', u'indicate', u'special', u'opponents', u'pander', u'little', u'nominate', u'frontier', u'voters', u'please', u'negative', u'unite', u'label', u'sciences', u'subjects', u'hood', u'forces', u'relate', u'lecture', u'msnbc', u'hardball', u'war', u'feminism', u'define', u'op-ed', u'regional', u'intend', u'myth', u'ruler', u'online', u'votes', u'outlying', u'observers', u'sachem', u'pandering', u'deaths', u'bolt', u'rationale', u'miranda', u'libby', u'spin', u'outpost', u'spain', u'formal', u'william', u'mondale', u'outline', u'fascism', u'argument', u'mandate', u'muckraker', u'provinces', u'scientist', u'nations', u'ideology', u'remain', u'transform', u'seeks', u'behavior', u'isolation', u'moral', u'registry', u'italian', u'soviet', u'two-step', u'gain']
    #board_size = 15
    #p = Puzzle(dictionary=words, x=board_size, y=board_size)
    #p.down_words[(1,1)] = [ 'arm', 'on your boady' ]
    #print p.javascriptOutput()
    #hints = p.generateHints(words)
    #print hints
    #hint_words = puz.down_words.values() + puz.across_words.values()
    #puz.generateHints(hint_words)
    
