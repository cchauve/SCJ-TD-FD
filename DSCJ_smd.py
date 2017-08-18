from sys import argv
import random
import networkx as nx
import matplotlib.pyplot as plt


#Using python 3 interpreter

#Function definitions
#---------------------------------------------------------------------------
#Gene in opposite direction. If gene is a string '-g', returns string 'g'. 
def negate(gene):
	if gene:
		return gene[1:] if gene[0] == '-' else str('-' + gene)
	else:
		return None

#Forms a list of all gene families in input genome.
def listGene(genome):
	gene_list = []
	for chromosome in genome:
		for gene in chromosome:
			if gene[0] == '-':
				if negate(gene) not in gene_list:
					gene_list.append(negate(gene))
			else:
				if gene not in gene_list:
					gene_list.append(gene)
	return gene_list

#Output genome as a list of lists.
def createGenome(substrings):
	genomes = [[] for i in range(2)]										#List of chromosomes, where chromosomes are lists of oriented genes
	seen = set()															#Set of genes in A to check for trivialness
	trivial = True
	gene_count = [0,0]														#Maintain a count of number of genes in A and D, respectively
	chr_type = [[] for i in range(2)]										#A log of each chromosome being linear ('L') or circular ('C') in form of lists 
	i = -1																	#Initialize chromosome index
	for line in substrings:
		if line[-1] not in {')','|'}:										#Skip lines that do not end with | or ), as they aren't chromosomes.
			i += 1
		elif line[-1] == '|':												#Linear chromosome
			line = line.split(' ')
			line = [x for x in line if x != '|']
			if i == 0:														#Check trivialness only for A.
				for gene in line:
					if gene not in seen and negate(gene) not in seen:		#Add gene to 'seen' set if not seen before 
						seen.add(gene)
					else:
						trivial = False
			genomes[i].append(line)
			gene_count[i] += len(line)
			chr_type[i].append('L')
		else:																#Circular chromosome
			line = line.split(' ')											#If circular chromosome, then add first gene after the last gene.
			line[-1] = line[0]												#For e.g., (a,b,c) = [a,b,c,a]. Required for tandem array check in circular chromosomes
			if i == 0:
				for gene in line[:-1]:
					if gene not in seen and negate(gene) not in seen:		#Add gene to 'seen' set if not seen before
						seen.add(gene)
					else:
						trivial = False
			genomes[i].append(line)
			gene_count[i] += len(line) - 1
			chr_type[i].append('C')
	if trivial == False:													#If gene repeats, A is nontrivial. Terminate program.
		print("Error message: Ancestor genome must be trivial.")
		quit()
	if set(listGene(genomes[0])) != set(listGene(genomes[1])):				#If A and D on different set of gene families, terminate program.
		print("Error message: Ancestor and descendant genomes have different sets of gene families.")
		quit()
	return (genomes, gene_count, chr_type)

#Counts TD from Arrays and reduces genome
def reduceGenome(D):
	TD_from_arrays = 0														#Maintain a count of TD from arrays.
	for chromosome in D:										
		for gene_idx in range(len(chromosome)):
			while gene_idx < len(chromosome) - 1:
				if chromosome[gene_idx] == chromosome[gene_idx + 1]:		#Remove tandem arrays, if any.
					del chromosome[gene_idx]	
					TD_from_arrays += 1
				else:
					gene_idx += 1
	return (D, TD_from_arrays)				

#Forms adjacency list of input genome
def listAdj(genome):
	adj_list = []															#List of adjacencies where 
	for chromosome in genome:												#every adjacency is of the format:
		for gene_idx in range(len(chromosome) - 1):							#[(g1,'h'/'t'),(g2,'h'/'t')]
			if chromosome[gene_idx][0] == '-':
				left = (chromosome[gene_idx][1:], 't')
			else:
				left = (chromosome[gene_idx], 'h')
			if chromosome[gene_idx + 1][0] == '-':
				right = (chromosome[gene_idx + 1][1:], 'h')
			else:
				right = (chromosome[gene_idx + 1], 't')
			adj_list.append([left, right])
	return adj_list

#Updates A_dict by relabeling gene matched with gene in A
def updateA(gene, A_dict):
	LN, RN = A_dict[gene]['LN'], A_dict[gene]['RN']							#Left and right neighbors in A
	if LN:																	#If Left neighbor exists, update corresponding entry.
		if LN[0] == '-':													#(If LN exists, its right neighbor will be the gene itself, 
			A_dict[LN[1:]]['RN'] = A_dict[LN[1:]]['RN']+str('copy')+str(1)	#so needs to be relabeled) 
		else: 
			A_dict[LN]['RN'] = A_dict[LN]['RN']+str('copy')+str(1) 
	if RN:																	#If Right neighbor exists, update corresponding entry.
		if RN[0] == '-': 													#(If RN exists, its left neighbor will be the gene itself,	
			A_dict[RN[1:]]['LN'] = A_dict[RN[1:]]['LN']+str('copy')+str(1)	#so needs to be relabeled)
		else: 
			A_dict[RN]['LN'] = A_dict[RN]['LN']+str('copy')+str(1)
	A_dict[gene+str('copy')+str(1)] = A_dict[gene]
	del A_dict[gene]
	return A_dict							

#Updates Idx_dict and D_dict by relabeling gene matched with gene in A
def updateD(gene, Idx_dict, A_dict, D_dict, index, i):
	Idx_dict[gene+str('copy')+str(i)] = [index]								#Update Idx_dict by introducing entry gcopy'i'
	Idx_dict[gene].remove(index)											#and removing corresponding index from Idx_dict[g]

	#if A_dict[gene]['Sign'] == D_dict[index]['Sign']:						#Update D_dict
	LNIdx, RNIdx = D_dict[index]['LNIdx'], D_dict[index]['RNIdx']				#Left and right neighbors in D
	if LNIdx: D_dict[LNIdx]['RN'] = D_dict[LNIdx]['RN']+str('copy')+str(i) 		#If LN exists, relabel its right neighbor
	if RNIdx: D_dict[RNIdx]['LN'] = D_dict[RNIdx]['LN']+str('copy')+str(i) 		#If RN exists, relabel its left neighbor
	#else:
	#	LNIdx, RNIdx = D_dict[index]['RNIdx'], D_dict[index]['LNIdx']				
	#	if LNIdx: D_dict[LNIdx]['LN'] = D_dict[LNIdx]['LN']+str('copy')+str(i) 		
	#	if RNIdx: D_dict[RNIdx]['RN'] = D_dict[RNIdx]['RN']+str('copy')+str(i) 		
	return Idx_dict, D_dict					

#Updates list of Floating Duplicates
def updateFD(FD, i, gene, Idx_dict, D_dict):
	for index in Idx_dict[gene]:
		FD.append(gene+str('copy')+str(i))									
		Idx_dict[gene+str('copy')+str(i)] = [index]
		LNIdx, RNIdx = D_dict[index]['LNIdx'], D_dict[index]['RNIdx']				#Left and right neighbors in D		
		if LNIdx: D_dict[LNIdx]['RN'] = D_dict[LNIdx]['RN']+str('copy')+str(i)		#If LN exists, relabel its right neighbor
		if RNIdx: D_dict[RNIdx]['LN'] = D_dict[RNIdx]['LN']+str('copy')+str(i)		#If RN exists, relabel its left neighbor
		i += 1
	return(FD, Idx_dict, D_dict)

#Adjacency weight function
def wtAdj(adj, adj_list):
	weight = 0
	for genome in adj_list:
		if adj in genome or adj[::-1] in genome:	
			weight += 1
	weight = 2*weight - len(adj_list)
	return weight

#Create MWM graph
def createGraph(adj_list, total_gene_list, total_adj_list):
	G = nx.Graph()
	for g in total_gene_list:
		G.add_node((g,'t'))
		G.add_node((g,'h'))
	edge_list = []
	for adj in total_adj_list:
		edge_list.append((adj[0],adj[1],wtAdj(adj, adj_list)))
	G.add_weighted_edges_from(edge_list)
	return G

#Max weight matching
def MWMedges(G, total_adj_list):
	kept_adj = []
	disc_adj = []
	adj_kept_mwm = {}
	adj_info = {}
	for adj in total_adj_list:
		adj_kept_mwm[tuple(adj)] = False
	M = nx.max_weight_matching(G)
	M_list = sorted(list(M.keys()))
	for m1 in M_list:
		m2 = M[m1]
		adj_kept_mwm[(m1,m2)] = True
	for adj in total_adj_list:
		if adj_kept_mwm[tuple(adj)] == True:
			kept_adj.append(tuple(adj))
		else:
			disc_adj.append(tuple(adj))
	return((kept_adj, disc_adj))		



#Main functions
#---------------------------------------------------------------------------
#Finds distance between the two given genomes in the input file
def distance(filename):
	string = open(filename, "r").read()
	substrings = string.split("\n")
	substrings = [line for line in substrings if line and line[0] != '#']	#Read line only if it is nonempty and not a comment.

	genomes, gene_count, chr_type = createGenome(substrings)	

	A = genomes[0]			
	D = genomes[1]			 
								
	D, TD_from_arrays = reduceGenome(D)

	gene_count[1] -= TD_from_arrays											#Number of genes in D after removing tandem arrays.
	n_duplicates = gene_count[1] - gene_count[0]							#Number of genes in D - number of genes in A

	A_adj = listAdj(A)
	D_adj = listAdj(D)

	preserved_adj = [adj for adj in A_adj if adj in D_adj or list(reversed(adj)) in D_adj]		#Intersection of adjacency sets, A and D
	n_cuts = len(A_adj) - len(preserved_adj)
	n_joins = len(D_adj) - len(preserved_adj)

	d_DSCJ = n_cuts + n_joins + 2*n_duplicates + TD_from_arrays				#d_DSCJ(A,D) = |A-D| + |D-A| + 2*n_d + TDA.

	print(d_DSCJ)
	print(n_cuts)
	print(n_joins)
	print(n_duplicates)
	print(TD_from_arrays)



#---------------------------------------------------------------------------
#Finds scenario with optimal distance to obtain second genome from first genome in the input file
#Data Structures:
#1. Both genomes are lists of chromosomes. (List of lists)
#2. Chromosomes are lists of oriented genes. (List)
#3. Genes are signed strings. (Strings)
#4. Three dictionaries:
#	A_dict contains - Key = gene. Value = (Idx (position), Sign (orientation), Left neighbor, Right neighbor)
#	Idx_dict contains - Key = Gene family, Value = List of indices (positions) of g in D.
#	D_dict contains - Key = Index (position). Value = (Sign (orientation), Left neighbor, Left neighbor index, Right neighbor, Right neighbor index) 
#5. Floating Duplicates and Tandem Duplicates (if required later). (Lists)
#6. A_adj and D_adj (Lists). Every adjacency is of the format: [(g1,'h'/'t'),(g2,'h'/'t')]
#7. Each duplicate gene has been relabeled as: g -> gcopy'i' for 'i'th instance of the gene.

#Pseudocode:

#Remove Tandem arrays if any. Complexity O(n_D)
#Create a dictionary for A. Complexity O(n_A) 
#Create an index dictionary for D: Key=gene name, Val=list of positions of gene in D
#Create a dictionary for D. Created along with index dictionary. Complexity O(n_D)
#Shuffle positions in A for randomness.
#
#For every gene g in A: Complexity O(n_A)
#	If g is from nontrivial family:
#		Check for context strongly conserved. Complexity O(copy number of g) 
#			If instance found: 
#           	Update all the dictionaries.
#		If instance found: 
#			Update list of FDs. Complexity O(copy number of g)
#		
#		If not strongly conserved:
#			Check for conservation of adjacencies on either side. Complexity O(copy number of g)
#			Check if context weakly conserved: Complexity O(copy number of g)
#				If instance found:
# 					Update all the dictionaries.
#				Else check only if left adj conserved:  
#					If so, update all the dictionaries accordingly.
#				Else check only if right adj conserved:  
#					If so, update all the dictionaries accordingly.
#				Else: 
#					Match with the first copy of g in D. Update all the dictionaries.
#
#			If weakly conserved:
#				Update list of FDs for remaining copies. Complexity O(copy number of g)	
#			Else not conserved:
#				Update list of FDs for remaining copies. Complexity O(copy number of g)
#
#Create an adjacency set of D using the dictionary. Complexity O(n_D)
#Create an adjacency set of A using the dictionary. Also add FDs. Complexity O(n_D)
#
#Find the distance: |A-D| + |D-A| + n_d + TDA																

def scenario(filename):
	string = open(filename, "r").read()
	substrings = string.split("\n")
	substrings = [line for line in substrings if line and line[0] != '#']	#Read line only if it is nonempty and not a comment.

	genomes, gene_count, chr_type = createGenome(substrings)

	A = genomes[0]
	D = genomes[1]		

	TD_from_arrays = 0														#Maintain a count of TD from arrays.

	D, TD_from_arrays = reduceGenome(D)
			
	A_dict = {}	#Dictionary for A. Key = gene. Value = (Idx, Sign, Left neighbor, Right neighbor)		
	for i in range(len(A)):
		if chr_type[0][i] == 'L':									
			for j in range(len(A[i])):								 
				if j == 0:
					if A[i][j][0] == '-':							
						A_dict[negate(A[i][j])] = {'Idx': (i,j), 'Sign': 'Neg', 'LN': None, 'RN': A[i][j+1]}
					else:
						A_dict[(A[i][j])] = {'Idx': (i,j), 'Sign': 'Pos', 'LN': None, 'RN': A[i][j+1]}
				elif j == len(A[i])-1:	
					if A[i][j][0] == '-':
						A_dict[negate(A[i][j])] = {'Idx': (i,j), 'Sign': 'Neg', 'LN': A[i][j-1], 'RN': None}
					else:
						A_dict[(A[i][j])] = {'Idx': (i,j), 'Sign': 'Pos', 'LN': A[i][j-1], 'RN': None}
				else:
					if A[i][j][0] == '-':
						A_dict[negate(A[i][j])] = {'Idx': (i,j), 'Sign': 'Neg', 'LN': A[i][j-1], 'RN': A[i][j+1]}
					else:
						A_dict[(A[i][j])] = {'Idx': (i,j), 'Sign': 'Pos', 'LN': A[i][j-1], 'RN': A[i][j+1]}					
		if chr_type[0][i] == 'C':									#If chromosome is circular, add appropriate neighbors for genes at both ends.
			A[i] = A[i][:-1]										#For e.g.: In (a,b,c) LN of a is c and RN of c is a.
			for j in range(len(A[i])):
				if j == 0:
					if A[i][j][0] == '-':
						A_dict[negate(A[i][j])] = {'Idx': (i,j), 'Sign': 'Neg', 'LN': A[i][-1], 'RN': A[i][j+1]}
					else:
						A_dict[(A[i][j])] = {'Idx': (i,j), 'Sign': 'Pos', 'LN': A[i][-1], 'RN': A[i][j+1]}
				elif j == len(A[i])-1:	
					if A[i][j][0] == '-':
						A_dict[negate(A[i][j])] = {'Idx': (i,j), 'Sign': 'Neg', 'LN': A[i][j-1], 'RN': A[i][0]}
					else:
						A_dict[(A[i][j])] = {'Idx': (i,j), 'Sign': 'Pos', 'LN': A[i][j-1], 'RN': A[i][0]}
				else:
					if A[i][j][0] == '-':
						A_dict[negate(A[i][j])] = {'Idx': (i,j), 'Sign': 'Neg', 'LN': A[i][j-1], 'RN': A[i][j+1]}
					else:
						A_dict[(A[i][j])] = {'Idx': (i,j), 'Sign': 'Pos', 'LN': A[i][j-1], 'RN': A[i][j+1]}										
	
	Idx_dict = {}	#Dictionary for indices. Key = Gene family, Value = List of positions of g in D. 
	D_dict = {}		#Dictionary for D. Key = Index. Value = (Sign, Left neighbor, Left neighbor index, Right neighbor, Right neighbor index)
	for i in range(len(D)):
		if chr_type[1][i] == 'L':									
			for j in range(len(D[i])):								 
				if D[i][j][0] == '-':								
					try:
						Idx_dict[negate(D[i][j])].append((i,j))
					except KeyError:
						Idx_dict[negate(D[i][j])] = [(i,j)]
					if j == 0: 
						D_dict[(i,j)] = {'Sign': 'Neg', 'LN': None, 'LNIdx': None, 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
					elif j == len(D[i])-1:
						D_dict[(i,j)] = {'Sign': 'Neg', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': None, 'RNIdx': None}
					else:
						D_dict[(i,j)] = {'Sign': 'Neg', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
				else:
					try:
						Idx_dict[D[i][j]].append((i,j))
					except KeyError:
						Idx_dict[D[i][j]] = [(i,j)]
					if j == 0:
						D_dict[(i,j)] = {'Sign': 'Pos', 'LN': None, 'LNIdx': None, 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
					elif j == len(D[i])-1:
						D_dict[(i,j)] = {'Sign': 'Pos', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': None, 'RNIdx': None}
					else:
						D_dict[(i,j)] = {'Sign': 'Pos', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
		if chr_type[1][i] == 'C':									#If chromosome is circular, add appropriate neighbors for genes at both ends.
			D[i] = D[i][:-1]										#For e.g.: In (a,b,c) LN of a is c and RN of c is a.
			for j in range(len(D[i])):
				if D[i][j][0] == '-':
					try:
						Idx_dict[negate(D[i][j])].append((i,j))
					except KeyError:
						Idx_dict[negate(D[i][j])] = [(i,j)]
					if j == 0:
						D_dict[(i,j)] = {'Sign': 'Neg', 'LN': D[i][-1], 'LNIdx': (i,len(D[i])-1), 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
					elif j == len(D[i])-1:
						D_dict[(i,j)] = {'Sign': 'Neg', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': D[i][0], 'RNIdx': (i,0)}
					else:
						D_dict[(i,j)] = {'Sign': 'Neg', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
				else:
					try:
						Idx_dict[D[i][j]].append((i,j))
					except KeyError:
						Idx_dict[D[i][j]] = [(i,j)]
					if j == 0:
						D_dict[(i,j)] = {'Sign': 'Pos', 'LN': D[i][-1], 'LNIdx': (i,len(D[i])-1), 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
					elif j == len(D[i])-1:
						D_dict[(i,j)] = {'Sign': 'Pos', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': D[i][0], 'RNIdx': (i,0)}
					else:
						D_dict[(i,j)] = {'Sign': 'Pos', 'LN': D[i][j-1], 'LNIdx': (i,j-1), 'RN': D[i][j+1], 'RNIdx': (i,j+1)}
					
	coords = []										#List of co-ordinates of A, shuffled for randomness							
	for i in range(len(A)):												
		for j in range(len(A[i])):
			coords.append([i,j])		
	random.shuffle(coords)

	FD = []											#List of FD created
	TD = []											#List of TD created

	for i, j in coords:
		gene = A[i][j]
		if gene[0] == '-':
			gene = negate(gene)

		if len(Idx_dict[gene]) > 1:
			#CASE 1: Context strongly conserved
			strong_context = 0
			weak_context = 0 															
			for index in Idx_dict[gene]:
				if strong_context == 0:														#Check for strong context if not already found
					if A_dict[gene]['Sign'] == D_dict[index]['Sign']:
						if A_dict[gene]['LN'] and A_dict[gene]['LN'] == D_dict[index]['LN'] and A_dict[gene]['RN'] and A_dict[gene]['RN'] == D_dict[index]['RN']:
							strong_context = 1
							A_dict = updateA(gene, A_dict)									#Updating A_dict							
							Idx_dict[gene+str('copy')+str(1)] = [index] 					#Updating Idx_dict and D_dict
							Idx_dict[gene].remove(index)
							LNIdx, RNIdx = D_dict[index]['LNIdx'], D_dict[index]['RNIdx']
							D_dict[LNIdx]['RN'] = D_dict[LNIdx]['RN']+str('copy')+str(1)
							D_dict[RNIdx]['LN'] = D_dict[RNIdx]['LN']+str('copy')+str(1)
					else:
						if A_dict[gene]['LN'] and A_dict[gene]['LN'] == negate(D_dict[index]['RN']) and A_dict[gene]['RN'] and A_dict[gene]['RN'] == negate(D_dict[index]['LN']):
							strong_context = 1
							A_dict = updateA(gene, A_dict)									#Updating A_dict
							Idx_dict[gene+str('copy')+str(1)] = [index] 					#Updating Idx_dict and D_dict
							Idx_dict[gene].remove(index)
							LNIdx, RNIdx = D_dict[index]['LNIdx'], D_dict[index]['RNIdx']
							D_dict[LNIdx]['RN'] = D_dict[LNIdx]['RN']+str('copy')+str(1)
							D_dict[RNIdx]['LN'] = D_dict[RNIdx]['LN']+str('copy')+str(1)
				
			if strong_context == 1:															#If strong conserved context, remaining genes matched with FDs
				FD, Idx_dict, D_dict = updateFD(FD, 2, gene, Idx_dict, D_dict)

			#If not Case 1, check for other cases.								
			if strong_context == 0:																
				left_adj_at, right_adj_at = None, None 		#Here left_adj_at (righ_adj_at) = position at which left (right) adjacency is found
				for index in Idx_dict[gene]:				#For every index in D having a copy of the gene, get right and left neighbors
					if not left_adj_at:														#Checking for left adjacency match
						if A_dict[gene]['Sign'] == D_dict[index]['Sign']:					
							if A_dict[gene]['LN'] and A_dict[gene]['LN'] == D_dict[index]['LN']:
								left_adj_at = index
						else:
							if A_dict[gene]['LN'] and A_dict[gene]['LN'] == negate(D_dict[index]['RN']):
								left_adj_at = index
					if not right_adj_at:													#Checking for right adjacency match	
						if A_dict[gene]['Sign'] == D_dict[index]['Sign']:						
							if A_dict[gene]['RN'] and A_dict[gene]['RN'] == D_dict[index]['RN']:
								right_adj_at = index
						else:
							if A_dict[gene]['RN'] and A_dict[gene]['RN'] == negate(D_dict[index]['LN']):
								right_adj_at = index

				#CASE 2: Context weakly conserved.				
				if left_adj_at and right_adj_at:
					weak_context = 1
					TD.append(gene)				
					
					Idx_dict, D_dict = updateD(gene, Idx_dict, A_dict, D_dict, left_adj_at, 1)		#Updating D by relabeling left match (to original gene in A)
					Idx_dict, D_dict = updateD(gene, Idx_dict, A_dict, D_dict, right_adj_at, 2)		#Updating D by relabeling right match (to tandem copy in A)
					
					LN, RN = A_dict[gene]['LN'], A_dict[gene]['RN']							#Updating A_dict
					Idx, Sign = A_dict[gene]['Idx'], A_dict[gene]['Sign']
					A_dict[gene+str('copy')+str(1)] = {'Idx': Idx, 'Sign': Sign, 'LN': LN, 'RN': RN}
					A_dict[gene+str('copy')+str(2)] = {'Idx': Idx, 'Sign': Sign, 'LN': LN, 'RN': RN}

					if LN[0] == '-':														#Introduce entry for TD in A_dict and relabel
						A_dict[LN[1:]]['RN'] = A_dict[LN[1:]]['RN']+str('copy')+str(1)		#Delete the gene from A_dict since it is now relabeled
						A_dict[gene+str('copy')+str(2)]['LN'] = A_dict[LN[1:]]['RN']
					else:
						A_dict[LN]['RN'] = A_dict[LN]['RN']+str('copy')+str(1)
						A_dict[gene+str('copy')+str(2)]['LN'] = A_dict[LN]['RN']
					if RN[0] == '-':
						A_dict[RN[1:]]['LN'] = A_dict[RN[1:]]['LN']+str('copy')+str(2)						
						A_dict[gene+str('copy')+str(1)]['RN'] = A_dict[RN[1:]]['LN']
					else:
						A_dict[RN]['LN'] = A_dict[RN]['LN']+str('copy')+str(2)
						A_dict[gene+str('copy')+str(1)]['RN'] = A_dict[RN]['LN']
					del A_dict[gene]

				#CASE 3: Context not conserved. Check for one match (left or right).	
				elif left_adj_at and not right_adj_at:
					Idx_dict, D_dict = updateD(gene, Idx_dict, A_dict, D_dict, left_adj_at, 1)		#Updating D by relabeling left match (to original gene in A)						
					A_dict = updateA(gene, A_dict)													#Updating A_dict

				elif right_adj_at and not left_adj_at:
					Idx_dict, D_dict = updateD(gene, Idx_dict, A_dict, D_dict, right_adj_at, 1)		#Updating D by relabeling right match (to original gene in A)						
					A_dict = updateA(gene, A_dict)													#Updating A_dict

				#CASE 4: Context not conserved. No adjacency conserved.			
				else:
					Idx_dict, D_dict = updateD(gene, Idx_dict, A_dict, D_dict, index, 1)	#Updating D by relabeling last copy (to original gene in A)						
					A_dict = updateA(gene, A_dict)											#Updating A_dict

				if left_adj_at and right_adj_at:											#If weakly conserved context, remaining genes matched with FDs
					FD, Idx_dict, D_dict = updateFD(FD, 3, gene, Idx_dict, D_dict)									
				else:																		#If context not conserved, remaining genes matched with FDs
					FD, Idx_dict, D_dict = updateFD(FD, 2, gene, Idx_dict, D_dict)									

	#All Cases covered. Create adjacency lists from dictionaries				
	D_adj = []													#Form adjacency set for relabeled genome D'							
	for x in sorted((k,v) for (k,v) in D_dict.items()):
		left, right = None, None
		if x[1]['RNIdx']:
			RNIdx = x[1]['RNIdx']
			if D_dict[RNIdx]['LN'][0] == '-':
				left = (D_dict[RNIdx]['LN'][1:], 't')
			else:
				left = (D_dict[RNIdx]['LN'], 'h')
			if D_dict[x[0]]['RN'][0] == '-': 
				right = (D_dict[x[0]]['RN'][1:], 'h')
			else:
				right = (D_dict[x[0]]['RN'], 't')
			D_adj.append([left, right])

	A_adj = []													#Form adjacency set for relabeled genome A'
	for x in sorted((v['Idx'],k) for (k,v) in A_dict.items()):
		left, right = None, None
		if A_dict[x[1]]['RN']:
			RN = A_dict[x[1]]['RN']
			if A_dict[x[1]]['Sign'] == 'Neg':
				left = (x[1], 't')
			else:
				left = (x[1], 'h')
			if RN[0] == '-':
				right = (RN[1:], 'h')
			else:
				right = (RN, 't')
			A_adj.append([left, right])			
	for x in FD:												#Append (g_h g_t) adjacencies for each FD
		A_adj.append([(x, 'h'),(x, 't')])

	preserved_adj = [adj for adj in A_adj if adj in D_adj or list(reversed(adj)) in D_adj]		#Intersection of adjacency sets, A' and D'
	n_cuts = len(A_adj) - len(preserved_adj)					#Adjacencies seen in A' but NOT preserved in D'
	n_joins = len(D_adj) - len(preserved_adj)					#Adjacencies seen in D' but NOT preserved from A'
	n_duplicates = len(FD) + len(TD)

	distance = n_cuts + n_joins + n_duplicates + TD_from_arrays	#d_DSCJ(A,D) = |A'-D'| + |D'-A'| + n_d + TDA.


	print(distance)
	print(n_cuts, n_joins)			
	print(len(FD), len(TD), TD_from_arrays)

	#outputfile = open("output1.txt", "w")
	#outputfile.write(str(A_adj))
	#outputfile.write("\n")
	#outputfile.write(str(D_adj))
					


#---------------------------------------------------------------------------
#Finds the median of all given genomes in the input file
def median(filename):
	string = open(filename, "r").read()
	substrings = string.split("\n")
	substrings = [line for line in substrings if line and line[0] != '#']
	genomes = []
	i = -1
	for line in substrings:
		if line[-1] not in {')','|'}:
			genomes.append([])
			i += 1
		elif line[-1] == '|':
			line = line.split(' ')
			line = [x for x in line if x != '|']
			genomes[i].append(line)	
		else:
			line = line.split(' ')
			line[-1] = line[0]
			genomes[i].append(line)

	TD_from_arrays = [0] * len(genomes)
	i = 0
	for genome in genomes:
		for chromosome in genome:				
			for gene_idx in range(len(chromosome)):
				while gene_idx < len(chromosome) - 1:
					if chromosome[gene_idx] == chromosome[gene_idx + 1]:
						del chromosome[gene_idx]
						TD_from_arrays[i] += 1
						print(TD_from_arrays[i])
					else:
						gene_idx += 1
		i += 1

	adj_list = []
	total_gene_list = []	
	for genome in genomes:
		adj_list.append(listAdj(genome))
		total_gene_list = list(set(total_gene_list + listGene(genome)))

	total_adj_list = []
	for genome in adj_list:
		for adj in genome:
			if adj in total_adj_list or adj[::-1] in total_adj_list:
				continue
			else:
				total_adj_list.append(adj)	

	G = createGraph(adj_list, total_gene_list, total_adj_list)
	M = nx.max_weight_matching(G)
	print(M)
	print(MWMedges(G, total_adj_list))
	
	pos=nx.spring_layout(G)
	nx.draw(G,pos,with_labels=True)
	nx.draw_networkx_edge_labels(G,pos)
	plt.axis('off')
	plt.show()
	

	

#Input
#---------------------------------------------------------------------------
if len(argv) < 3:															#Takes file with genomes as argument in command line		
	print('Usage: python DSCJ_smd.py -d/-s/-m <genome_file>')
	exit(1)

if argv[1] == '-d':
	distance(argv[2])
elif argv[1] == '-s':
	scenario(argv[2])
elif argv[1] == '-m':
	median(argv[2])
else:
	print('Incorrect usage')
	print('Usage: python DSCJ_smd.py -d/-s/-m <genome_file>')