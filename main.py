import sys
import os, platform
import io
from PyQt5 import QtWidgets, Qt, QtGui, QtCore, uic
from CoTargeting import CoTargeting
from closingWin import closingWindow
from Results import Results
from NewGenome import NewGenome
from NewEndonuclease import NewEndonuclease
import genomeBrowser
import gzip
import webbrowser
import requests
import GlobalSettings
import multitargeting
from AnnotationParser import Annotation_Parser
from export_to_csv import export_csv_window
from generateLib import genLibrary
from Algorithms import SeqTranslate
from CSPRparser import CSPRparser
import populationAnalysis
import platform
import ncbi
import glob

# =========================================================================================
# CLASS NAME: AnnotationsWindow
# Inputs: Annotation file and search query from MainWindow
# Outputs: Greg: AnnotationWindow showing entries matching search query 
# =========================================================================================

class AnnotationsWindow(QtWidgets.QMainWindow):

    def __init__(self, info_path):
        super(AnnotationsWindow, self).__init__()
        uic.loadUi(GlobalSettings.appdir + 'Annotation Details.ui', self)
        self.setWindowIcon(QtGui.QIcon(GlobalSettings.appdir + "cas9image.png"))
        self.Submit_button.clicked.connect(self.submit)
        self.Go_Back_Button.clicked.connect(self.go_Back)
        self.select_all_checkbox.stateChanged.connect(self.select_all_genes)
        self.mainWindow = ""
        self.type = ""
        self.mwfg = self.frameGeometry()  ##Center window
        self.cp = QtWidgets.QDesktopWidget().availableGeometry().center()  ##Center window
        self.tableWidget.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tableWidget.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableWidget.setAutoScroll(False)


    def submit(self):
        self.mainWindow.collect_table_data_nonkegg()
        self.hide()
        self.mainWindow.mwfg.moveCenter(self.mainWindow.cp)  ##Center window
        self.mainWindow.move(self.mainWindow.mwfg.topLeft())  ##Center window
        self.mainWindow.show()


    def go_Back(self):
        self.tableWidget.clear()
        self.mainWindow.checkBoxes.clear()
        self.mainWindow.searches.clear()
        self.tableWidget.setColumnCount(0)
        self.mainWindow.mwfg.moveCenter(self.mainWindow.cp)  ##Center window
        self.mainWindow.move(self.mainWindow.mwfg.topLeft())  ##Center window
        self.mainWindow.show()
        self.mainWindow.progressBar.setValue(0)
        self.hide()


    # this function is very similar to the other fill_table, it just works with the other types of annotation files
    def fill_table_nonKegg(self, mainWindow):
        self.tableWidget.clearContents()
        self.mainWindow = mainWindow
        self.tableWidget.setColumnCount(4)
        self.mainWindow.progressBar.setValue(85)
        self.tableWidget.setHorizontalHeaderLabels(["Gene ID","Gene Name/Locus Tag","Chromosome/Scaffold #","Description"])
        header = self.tableWidget.horizontalHeader()
        mainWindow.checkBoxes = []
        self.type = "nonkegg"
        index = 0
        for searchValue in mainWindow.searches:
            for definition in mainWindow.searches[searchValue]:
                for gene in mainWindow.searches[searchValue][definition]:
                    if (gene[2] == 'gene' or gene[2] == 'tRNA' or gene[2] == 'rRNA'):
                        self.tableWidget.setRowCount(index + 1)
                        temp_list = definition.split(";")
                        temp_len = len(temp_list)
                        # set the checkbox
                        #ckbox = QtWidgets.QCheckBox()
                        #self.tableWidget.setCellWidget(index, 4, ckbox)

                        # set the description part of the window as well as set the correct data for the checkbox
                        defin_obj = QtWidgets.QTableWidgetItem(temp_list[-1])
                        self.tableWidget.setItem(index, 3, defin_obj)
                        mainWindow.checkBoxes.append([definition])
                        mainWindow.checkBoxes[len(mainWindow.checkBoxes) - 1].append(gene)
                        mainWindow.checkBoxes[len(mainWindow.checkBoxes) - 1].append(index)

                        # set the Gene Name/Locus Tag in the window
                        type_obj = QtWidgets.QTableWidgetItem(temp_list[temp_len-2])
                        self.tableWidget.setItem(index, 1, type_obj)

                        # set the gene id in the window
                        gene_id_obj = QtWidgets.QTableWidgetItem(gene[0])
                        self.tableWidget.setItem(index, 0, gene_id_obj)

                        chrom_number = QtWidgets.QTableWidgetItem(str(gene[1]))
                        self.tableWidget.setItem(index, 2, chrom_number)

                        index += 1
                    if index >= 1000:
                        break
                if index >= 1000:
                    break
            if index >= 1000:
                break

        index = 0
        self.tableWidget.resizeColumnsToContents()
        mainWindow.hide()
        self.mwfg.moveCenter(self.cp)  ##Center window
        self.move(self.mwfg.topLeft())  ##Center window
        self.show()
        return 0

    # this is the connection for the select all checkbox
    # selects/deselects all the genes in the table
    def select_all_genes(self):
        # check to see if we're selecting all of them or not
        if self.select_all_checkbox.isChecked():
            select_all = True
        else:
            select_all = False

        # # go through and do the selection
        # for i in range(self.tableWidget.rowCount()):
        #     #self.tableWidget.cellWidget(i, 4).setChecked(select_all)
        if select_all == True:
            self.tableWidget.selectAll()
        else:
            self.tableWidget.clearSelection()


    # this function calls the closingWindow class.
    def closeEvent(self, event):
        GlobalSettings.mainWindow.closeFunction()
        event.accept()


# =========================================================================================
# CLASS NAME: CMainWindow
# Inputs: Takes in the path information from the startup window and also all input parameters
# that define the search for targets e.g. endonuclease, organism genome, gene target etc.
# Outputs: The results of the target search process by generating a new Results window
# =========================================================================================


class CMainWindow(QtWidgets.QMainWindow):

    def __init__(self, info_path):
        super(CMainWindow, self).__init__()
        uic.loadUi(GlobalSettings.appdir + 'CASPER_main.ui', self)
        self.dbpath = ""
        self.info_path = info_path
        self.TNumbers = {}  # the T numbers from a kegg search
        self.orgcodes = {}  # Stores the Kegg organism code by the format {full name : organism code}
        self.gene_list = {}  # list of genes (no ides what they pertain to
        self.searches = {}
        self.checkBoxes = []
#        self.add_orgo = []
        self.checked_info = {}
        self.check_ntseq_info = {}  # the ntsequences that go along with the checked_info
        self.annotation_parser = Annotation_Parser()
        self.link_list = list()  # the list of the downloadable links from the NCBI search
        self.organismDict = dict()  # the dictionary for the links to download. Key is the description of the organism, value is the ID that can be found in link_list
        self.organismData = list()
        self.ncbi = ncbi.NCBI_search_tool()
        self.ncbi.hide()

        # --- Style Modifications --- #
        groupbox_style = """
        QGroupBox:title{subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px 0 5px;}
        QGroupBox#Step1{border: 2px solid rgb(111,181,110);
                        border-radius: 9px;
                        font: 15pt "Arial";
                        font: bold;
                        margin-top: 10px;}"""

        self.Step1.setStyleSheet(groupbox_style)
        self.Step2.setStyleSheet(groupbox_style.replace("Step1", "Step2"))
        self.Step3.setStyleSheet(groupbox_style.replace("Step1", "Step3"))

        # --- Button Modifications --- #


        #self.setWindowIcon(QtGui.QIcon(GlobalSettings.appdir.encode()))
        self.setWindowIcon(QtGui.QIcon(GlobalSettings.appdir + 'cas9image.png'))
        self.pushButton_FindTargets.clicked.connect(self.gather_settings)
        self.pushButton_ViewTargets.clicked.connect(self.view_results)
        self.pushButton_ViewTargets.setEnabled(False)
        self.GenerateLibrary.setEnabled(False)
        self.radioButton_Gene.clicked.connect(self.toggle_annotation)
        self.radioButton_Position.clicked.connect(self.toggle_annotation)

        self.seq_label.hide()

        self.actionUpload_New_Genome.triggered.connect(self.launch_newGenome)
        self.actionUpload_New_Endonuclease.triggered.connect(self.launch_newEndonuclease)
        self.actionOpen_Genome_Browser.triggered.connect(self.launch_newGenomeBrowser)
#        self.Add_Orgo_Button.clicked.connect(self.add_Orgo)
#        self.Remove_Organism_Button.clicked.connect(self.remove_Orgo)
#        self.endoChoice.currentIndexChanged.connect(self.endo_Changed)
        self.GenerateLibrary.clicked.connect(self.prep_genlib)
        self.actionExit.triggered.connect(self.close_app)
        self.visit_repo.triggered.connect(self.visit_repo_func)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.reset()
        self.Annotation_Window = AnnotationsWindow(info_path)

        # Hide Added orgo boxes
#        self.Added_Org_Combo.hide()
#        self.Remove_Organism_Button.hide()
#        self.Added_Org_Label.hide()
        # --- Menubar commands --- #
        self.actionChange_Directory.triggered.connect(self.change_directory)
        self.actionMultitargeting.triggered.connect(self.changeto_multitargeting)
        self.actionPopulation_Analysis.triggered.connect(self.changeto_population_Analysis)
        self.actionNCBI.triggered.connect(self.open_ncbi_web_page)
        self.actionCasper2.triggered.connect(self.open_casper2_web_page)
        self.actionNCBI_BLAST.triggered.connect(self.open_ncbi_blast_web_page)

#        self.Question_Button_add_org.clicked.connect(self.add_org_popup)


        # --- Setup for Gene Entry Field --- #
        self.geneEntryField.setPlainText("Example Inputs: \n\n"
                                         "Gene (ID, Locus Tag, or Name): 854068/YOL086C/ADH1 for S. cerevisiae alcohol dehydrogenase 1\n\n"
                                         "Position: chromosome,start,stop\n\n"
                                         "*Note: multiple entries must be separated by new lines*")
        # show functionalities on window
        self.newGenome = NewGenome(info_path)
        self.newEndonuclease = NewEndonuclease()
        self.CoTargeting = CoTargeting(info_path)
        self.Results = Results()
#        self.gene_viewer_settings = geneViewer()
        self.export_csv_window = export_csv_window()
        self.genLib = genLibrary()
        self.myClosingWindow = closingWindow()
        self.mwfg = self.frameGeometry()  ##Center window
        self.cp = QtWidgets.QDesktopWidget().availableGeometry().center()  ##Center window
        #self.actionUpload_New_Genome.setEnabled(False)
        self.genomebrowser = genomeBrowser.genomebrowser()
        #GlobalSettings.mainWindow.ncbi = ncbi.NCBI_search_tool()
        self.launch_ncbi_button.clicked.connect(self.launch_ncbi)

    # this function prepares everything for the generate library function
    # it is very similar to the gather settings, how ever it stores the data instead of calling the Annotation Window class
    # it moves the data onto the generateLib function, and then opens that window
    def prep_genlib(self):
        #print("prep genlib")
        # make sure the user actually inputs something
        inputstring = str(self.geneEntryField.toPlainText())
        if (inputstring.startswith("Example Inputs:") or inputstring == ""):
            QtWidgets.QMessageBox.question(self, "Error",
                                           "No gene has been entered.  Please enter a gene.",
                                           QtWidgets.QMessageBox.Ok)
        else:
            # standardize the input
            inputstring = inputstring.lower()
            found_matches_bool = True

            # call the respective function
            self.progressBar.setValue(10)
            if self.radioButton_Gene.isChecked():
                if len(self.checked_info) > 0:
                    found_matches_bool = True
                else:
                    found_matches_bool = False
            elif self.radioButton_Position.isChecked() or self.radioButton_Sequence.isChecked():
                QtWidgets.QMessageBox.question(self, "Error", "Generate Library can only work with gene names (Locus ID).",
                                               QtWidgets.QMessageBox.Ok)
                return
            """
            elif self.radioButton_Position.isChecked():
                pinput = inputstring.split(';')
                found_matches_bool = self.run_results("position", pinput,openAnnoWindow=False)
            elif self.radioButton_Sequence.isChecked():
                sinput = inputstring
                found_matches_bool = self.run_results("sequence", sinput, openAnnoWindow=False)
            """
            # if matches are found
            if found_matches_bool == True:
                # get the cspr file name
                cspr_file = self.organisms_to_files[self.orgChoice.currentText()][self.endoChoice.currentText()][0]
                if platform.system() == 'Windows':
                    cspr_file = GlobalSettings.CSPR_DB + '\\' + cspr_file
                else:
                    cspr_file = GlobalSettings.CSPR_DB + '/' + cspr_file
                kegg_non = 'non_kegg'

                # launch generateLib
                self.progressBar.setValue(100)

                # calculate the total number of matches found
                #
                # print(self.checked_info)
                # print(self.searches['d'].keys())
                genes = self.checked_info.keys()
                self.newsearches = {}

                for gene in genes:
                    for searches in self.searches.keys():
                        if gene in self.searches[searches].keys():
                            self.newsearches[gene] = self.searches[searches][gene]

                tempSum = len(self.checked_info)

                # warn the user if the number is greater than 50
                if tempSum > 50:
                    error = QtWidgets.QMessageBox.question(self, "Many Matches Found",
                                                           "More than 50 matches have been found. Continuing could cause a slow down...\n\n"
                                                           "Do you wish to continue?",
                                                           QtWidgets.QMessageBox.Yes |
                                                           QtWidgets.QMessageBox.No,
                                                           QtWidgets.QMessageBox.No)
                    if (error == QtWidgets.QMessageBox.No):
                        self.searches.clear()
                        self.progressBar.setValue(0)
                        return -2

                self.genLib.launch(self.newsearches,cspr_file, kegg_non)
            else:
                self.progressBar.setValue(0)


    # Function for collecting the settings from the input field and transferring them to run_results
    def gather_settings(self):
        inputstring = str(self.geneEntryField.toPlainText())

        # Error check: make sure the user actually inputs something
        if (inputstring.startswith("Example Inputs:") or inputstring == ""):
            QtWidgets.QMessageBox.question(self, "Error",
                                           "No gene has been entered. Please enter a gene.",
                                           QtWidgets.QMessageBox.Ok)
        else:
            # standardize the input
            inputstring = inputstring.lower()

            self.progressBar.setValue(10)
            if self.radioButton_Gene.isChecked():
                ginput = inputstring.split(',')
                self.run_results("gene", ginput)
            elif self.radioButton_Position.isChecked():
                self.run_results("position", inputstring)
            elif self.radioButton_Sequence.isChecked():
                sinput = inputstring
                self.run_results("sequence", sinput)


    # ---- Following functions are for running the auxillary algorithms and windows ---- #
    # this function is parses the annotation file given, and then goes through and goes onto results
    # it will call other versions of collect_table_data and fill_table that work with these file types
    # this function should work with the any type of annotation file, besides kegg.
    # this assumes that the parsers all store the data the same way, which gff and feature table do
    # please make sure the gbff parser stores the data in the same way
    # so far the gff files seems to all be different. Need to think about how we want to parse it
    def run_results_own_ncbi_file(self, inputstring, fileName, openAnnoWindow=True):
        #print("run ncbi results")
        self.annotation_parser = Annotation_Parser()

        #get complete path of file
        for file in glob.glob(GlobalSettings.CSPR_DB + "/**/*.gbff", recursive=True):
            if file.find(fileName) != -1:
                self.annotation_parser.annotationFileName = file
                break

        fileType = self.annotation_parser.find_which_file_version()

        # if the parser retuns the 'wrong file type' error
        if fileType == -1:
            QtWidgets.QMessageBox.question(self, "Error:",
                                           "We cannot parse the file type given. Please make sure to choose a GBFF, GFF, or Feature Table file."
                                           , QtWidgets.QMessageBox.Ok)
            self.progressBar.setValue(0)
            return

        self.progressBar.setValue(60)

        # this bit may not be needed here. Just a quick error check to make sure the chromosome numbers match

        cspr_file = self.organisms_to_files[self.orgChoice.currentText()][self.endoChoice.currentText()][0]
        if platform.system() == 'Windows':
            cspr_file = GlobalSettings.CSPR_DB + '\\' + cspr_file
        else:
            cspr_file = GlobalSettings.CSPR_DB + '/' + cspr_file

        own_cspr_parser = CSPRparser(cspr_file)
        own_cspr_parser.read_first_lines()

        if len(own_cspr_parser.karystatsList) != self.annotation_parser.max_chrom:
            QtWidgets.QMessageBox.question(self, "Warning:",
                                           "The number of chromosomes do not match. This could cause errors."
                                           , QtWidgets.QMessageBox.Ok)

#        # now go through and search for the actual locus tag, in the case the user input that
        searchValues = self.separate_line(inputstring[0])
        self.searches.clear()
#        for search in searchValues:
#            search = self.removeWhiteSpace(search)
#            if len(search) == 0:
#                continue
#
#            # set the searches dict of search equal to a new dictionary
#            self.searches[search] = {}
#
#            # upper case it, because the files seem to be all uppercase for this part
#            checkNormalDict = search.upper()
#            if checkNormalDict in self.annotation_parser.reg_dict:  # if it is in the normal dictionary
#                for item in self.annotation_parser.reg_dict[checkNormalDict]:  # for each list item in that position
#                    if item[0] not in self.searches[search]:  # if its not in the search's position yet
#                        self.searches[search][item[0]] = self.annotation_parser.reg_dict[checkNormalDict]
#                    elif item not in self.searches[search][
#                        item[0]]:  # assume it is in the searches position, but do not store duplicates
#                        self.searches[search][item[0]].append(self.annotation_parser.reg_dict[checkNormalDict])
#        if len(self.searches[searchValues[0]]) >= 1:  # if the previous search yielded results, do not continue
#            if openAnnoWindow:
#                self.Annotation_Window.fill_table_nonKegg(self)
#                return
#            else:
#                return True

        self.progressBar.setValue(75)
        # reset, and search the parallel dictionary now
        self.searches = {}
        for search in searchValues:
            search = self.removeWhiteSpace(search)
            if len(search) == 0:
                continue

            self.searches[search] = {}
            for item in self.annotation_parser.para_dict:
                checkingItem = item.lower()  # lowercase now, to match the user's input
                if search in checkingItem:  # if what they are searching for is somewhere in that key
                    if self.annotation_parser.para_dict[item][0] != '':
                        for match in self.annotation_parser.reg_dict[self.annotation_parser.para_dict[item][0]]:
                            if item not in self.searches[search]:
                                self.searches[search][item] = [match]
                            elif item not in self.searches[search][item]:
                                self.searches[search][item].append(match)
        # if the search returns nothing, throw an error
        if len(self.searches[searchValues[0]]) <= 0:
            QtWidgets.QMessageBox.question(self, "No Matches Found",
                                           "No matches found with that search, please try again.",
                                           QtWidgets.QMessageBox.Ok)
            self.progressBar.setValue(0)
            if openAnnoWindow:
                return
            else:
                return False

        # if we get to this point, that means that the search yieleded results, so fill the table
        self.progressBar.setValue(80)
        # check whether this function call is for Annotation Window, or for generate Lib
        if openAnnoWindow:
            self.Annotation_Window.fill_table_nonKegg(self)
        else:
            return True


    def run_results(self, inputtype, inputstring, openAnnoWindow=True):
        #print("run results")
        if(str(self.annotation_files.currentText()).find('.gbff') == -1):
            QtWidgets.QMessageBox.information(self, "Genomebrowser Error", "Filetype must be GBFF.",
                                              QtWidgets.QMessageBox.Ok)
            self.progressBar.setValue(0)
            return


        progvalue = 15
        self.searches = {}
        self.gene_list = {}
        self.progressBar.setValue(progvalue)

#        self.Results.change_start_end_button.setEnabled(False)
        self.Results.displayGeneViewer.setChecked(0)

        if inputtype == "gene":
            # make sure an annotation file has been selected
            if self.annotation_files.currentText() == "":
                error = QtWidgets.QMessageBox.question(self, "No Annotation", "Please select an annotation from NCBI or provide you own annotation file", QtWidgets.QMessageBox.Ok)
                self.progressBar.setValue(0)
                return
            # this now just goes onto the other version of run_results
            myBool = self.run_results_own_ncbi_file(inputstring, self.annotation_files.currentText(), openAnnoWindow=openAnnoWindow)
            if not openAnnoWindow:
                return myBool
            else:
                self.progressBar.setValue(0)
                return

        # position code below
        if inputtype == "position":
            inputstring = inputstring.replace(' ', '')
            searchInput = inputstring.split('\n')
            full_org = str(self.orgChoice.currentText())
            self.checked_info.clear()
            self.check_ntseq_info.clear()

            for item in searchInput:
                searchIndicies = item.split(',')
                # make sure the right amount of arguments were passed
                if len(searchIndicies) != 3:
                    QtWidgets.QMessageBox.question(self, "Position Error: Invalid Input",
                                                   "There are 3 arguments required for this function: chromosome, start position, and end position.",
                                                   QtWidgets.QMessageBox.Ok)
                    self.progressBar.setValue(0)
                    return

                # make sure user inputs digits
                if not searchIndicies[0].isdigit() or not searchIndicies[1].isdigit() or not searchIndicies[2].isdigit():
                    QtWidgets.QMessageBox.question(self, "Position Error: Invalid Input",
                                                   "The positions given must be integers. Please try again.",
                                                   QtWidgets.QMessageBox.Ok)
                    self.progressBar.setValue(0)
                    return
                # make sure start is less than end
                elif int(searchIndicies[1]) >= int(searchIndicies[2]):
                    QtWidgets.QMessageBox.question(self, "Position Error: Start Must Be Less Than End",
                                                   "The start index must be less than the end index.",
                                                   QtWidgets.QMessageBox.Ok)
                    self.progressBar.setValue(0)
                    return
                # append the data into the checked_info
                tempString = 'chrom: ' + str(searchIndicies[0]) + ' start: ' + str(searchIndicies[1]) + ' end: ' + str(searchIndicies[2])
                self.checked_info[tempString] = (int(searchIndicies[0]), int(searchIndicies[1]), int(searchIndicies[2]))

            self.progressBar.setValue(50)
            self.Results.transfer_data(full_org, self.organisms_to_files[full_org], [str(self.endoChoice.currentText())], os.getcwd(), self.checked_info, self.check_ntseq_info, "")
            self.progressBar.setValue(100)
            self.pushButton_ViewTargets.setEnabled(True)
            self.GenerateLibrary.setEnabled(True)

        # sequence code below
        if inputtype == "sequence":
            checkString = 'AGTCN'
            self.checked_info.clear()
            self.progressBar.setValue(10)
            inputstring = inputstring.upper()

            # check to make sure that the use gave a long enough sequence
            if len(inputstring) < 100:
                QtWidgets.QMessageBox.question(self, "Error",
                                               "The sequence given is too small. At least 100 characters are required.",
                                               QtWidgets.QMessageBox.Ok)
                self.progressBar.setValue(0)
                return

            # give a warning if the length of the sequence is long
            if len(inputstring) > 30000:
                error = QtWidgets.QMessageBox.question(self, "Large Sequence Detected",
                                                       "The sequence given is a large one and could slow down the process.\n\n"
                                                       "Do you wish to continue?",
                                                       QtWidgets.QMessageBox.Yes |
                                                       QtWidgets.QMessageBox.No,
                                                       QtWidgets.QMessageBox.No)
                if (error == QtWidgets.QMessageBox.No):
                    self.progressBar.setValue(0)
                    return

            # make sure all the chars are one of A, G, T, C, or N
            for letter in inputstring:
                # skip the end line character
                if letter == '\n':
                    continue
                if letter not in checkString:
                    QtWidgets.QMessageBox.question(self, "Sequence Error",
                                                   "The sequence must consist of A, G, T, C, or N. No other characters are allowed.",
                                                   QtWidgets.QMessageBox.Ok)
                    self.progressBar.setValue(0)
                    return
            self.progressBar.setValue(30)

            # build the CSPR file, and go into results
            fna_file_path = GlobalSettings.CSPR_DB + '/temp.fna'
            self.checked_info['Sequence Finder'] = (1, 0, len(inputstring))
            self.check_ntseq_info['Sequence Finder'] = inputstring.replace('\n', '')
            outFile = open(fna_file_path, 'w')
            outFile.write('>temp org here\n')
            outFile.write(inputstring)
            outFile.write('\n\n')
            outFile.close()
            self.progressBar.setValue(55)


    def launch_newGenome(self):
        self.hide()
        self.newGenome.mwfg.moveCenter(self.newGenome.cp)  ##Center window
        self.newGenome.move(self.newGenome.mwfg.topLeft())  ##Center window
        #update endo list
        self.newGenome.fillEndo()
        #show new genome window
        self.newGenome.show()


    def launch_newEndonuclease(self):
        self.newEndonuclease.show()


    def launch_newGenomeBrowser(self):
        print("creating graph")
        self.genomebrowser.createGraph(self)


    def launch_ncbi(self):
        QtWidgets.QMessageBox.information(self, "Note:",
        "NCBI Annotation Guidelines:\n\nDownload annotation files of the exact species and strain used in Analyze New Genome.\n\nMismatched annotation files will inhibit downstream analyses.",
        QtWidgets.QMessageBox.Ok)
        self.ncbi.show()


    # this function does the same stuff that the other collect_table_data does, but works with the other types of files
    def collect_table_data_nonkegg(self):
        # start out the same as the other collect_table_data
        self.checked_info.clear()
        self.check_ntseq_info.clear()
        full_org = str(self.orgChoice.currentText())
        holder = ()
        selected_indices = []
        selected_rows = self.Annotation_Window.tableWidget.selectionModel().selectedRows()
        for ind in sorted(selected_rows):
            selected_indices.append(ind.row())

        for item in self.checkBoxes:
            if item[2] in selected_indices:
                # if they searched base on Locus Tag
                if item[0] in self.annotation_parser.reg_dict:
                    # go through the dictionary, and if they match, store the item in holder
                    for match in self.annotation_parser.reg_dict[item[0]]:
                        if item[1] == match:
                            holder = (match[1], match[3], match[4])
                            self.checked_info[item[0]] = holder
                else:
                    # now we need to go through the para_dict
                    for i in range(len(self.annotation_parser.para_dict[item[0]])):
                        # now go through the matches in the normal dict's data
                        for match in self.annotation_parser.reg_dict[self.annotation_parser.para_dict[item[0]][i]]:
                            # if they match, store it in holder
                            if item[1] == match:
                                holder = (match[1], match[3], match[4])
                                self.checked_info[item[0]] = holder
        #print(self.checked_info)
        # now call transfer data
        self.progressBar.setValue(95)
        self.Results.transfer_data(full_org, self.organisms_to_files[full_org], [str(self.endoChoice.currentText())], os.getcwd(),
                                   self.checked_info, self.check_ntseq_info, "")
        self.progressBar.setValue(100)
        self.pushButton_ViewTargets.setEnabled(True)
        self.GenerateLibrary.setEnabled(True)


    # ------------------------------------------------------------------------------------------------------ #

    # ----- Following Code is helper functions for processing input data ----- #
    def separate_line(self, input_string):
        export_array = []
        while True:
            index = input_string.find('\n')
            if index == -1:
                if len(input_string) == 0:
                    return export_array
                else:
                    export_array.append(input_string)
                    return export_array
            export_array.append(input_string[:index])
            input_string = input_string[index + 1:]


    def removeWhiteSpace(self, strng):
        while True:
            if len(strng) == 0 or (strng[0] != " " and strng[0] != "\n"):
                break
            strng = strng[1:]
        while True:
            if len(strng) == 0 or (strng[len(strng) - 1] != " " and strng[0] != "\n"):
                return strng
            strng = strng[:len(strng) - 1]


    # Function to enable and disable the Annotation function if searching by position or sequence
    def toggle_annotation(self):
        if self.radioButton_Gene.isChecked():
            self.Step2.setEnabled(True)
        else:
            self.Step2.setEnabled(True)

        # check to see if the sequence button is pressed, and act accordingly -- OLD code
        # elif self.radioButton_Sequence.isChecked():
        #     self.Step2.setEnabled(False)
        #     mySeq = SeqTranslate()
        #     seq_checker = False
        #     # time to reset the endo's
        #     self.endoChoice.clear()
        #     for item in mySeq.endo_info:
        #         self.endoChoice.addItem(item)
        # else:
        #     self.Step2.setEnabled(False)
        #     seq_checker = True
        #     self.changeEndos()

        #self.orgChoice.setEnabled(seq_checker)


    def fill_annotation_dropdown(self):
        #recursive search for all .gbff in casper db folder
        self.annotation_files.clear()
        annotation_files = glob.glob(GlobalSettings.CSPR_DB + "/**/*.gbff", recursive=True)
        if platform.system() == "Windows":
            for i in range(len(annotation_files)):
                annotation_files[i] = annotation_files[i].replace("/","\\")
                annotation_files[i] = annotation_files[i][annotation_files[i].rfind("\\") + 1:]
        else:
            for i in range(len(annotation_files)):
                annotation_files[i] = annotation_files[i].replace("\\","/")
                annotation_files[i] = annotation_files[i][annotation_files[i].rfind("/") + 1:]

        annotation_files.sort(key=str.lower)
        self.annotation_files.addItems(annotation_files)

    def make_dictonary(self):
        url = "https://www.genome.jp/dbget-bin/get_linkdb?-t+genes+gn:" + self.TNumbers[
            self.Annotations_Organism.currentText()]
        source_code = requests.get(url, verify=False)
        plain_text = source_code.text
        buf = io.StringIO(plain_text)

        while True:
            line = buf.readline()
            if line[0] == "-":
                break
        while True:
            line = buf.readline()
            if line[1] != "a":
                return
            line = line[line.find(">") + 1:]
            seq = line[line.find(":") + 1:line.find("<")]
            line = line[line.find(">") + 1:]

            i = 0
            while True:
                if line[i] == " ":
                    i = i + 1
                else:
                    break
            key = line[i:line.find("\n") - 1]
            if key in self.gene_list:
                if seq not in self.gene_list[key]:
                    self.gene_list[key].append(seq)
            else:
                self.gene_list[key] = [seq]
            z = 5


    def organism_finder(self, long_str):
        semi = long_str.find(";")
        index = 1
        while True:
            if long_str[semi - index] == " ":
                break
            index = index + 1
        return long_str[:semi - index]


    # This method is for testing the execution of a button call to make sure the button is linked properly
    def testexe(self):
        choice = QtWidgets.QMessageBox.question(self, "Extract!", "Are you sure you want to quit?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice == QtWidgets.QMessageBox.Yes:
            # print(self.orgChoice.currentText())
            sys.exit()
        else:
            pass


#    def addOrgoCombo(self):
#        self.Add_Orgo_Combo.addItem("Select Organism")
#        for item in self.orgnanism_to_endos:
#            if (self.endoChoice.currentText() in self.organism_to_endos[item]) and (item != str(self.orgChoice.currentText())):
#                self.Add_Orgo_Combo.addItem(item)


    # ----- CALLED IN STARTUP WINDOW ------ #
    def getData(self):
        try:
            self.orgChoice.currentIndexChanged.disconnect()
        except:
            pass

        self.orgChoice.clear()
        self.endoChoice.clear()
        mypath = os.getcwd()
        found = False
        self.dbpath = mypath
        onlyfiles = [str(f) for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
        onlyfiles.sort(key=str.lower)
        self.organisms_to_files = {}
        self.organisms_to_endos = {}
        first = True
        for file in onlyfiles:
            if file.find('.cspr') != -1:
                if first == True:
                    first = False
                found = True
                newname = file[0:-4]
                endo = newname[newname.rfind("_")+1:-1]
                hold = gzip.open(file, 'r')
                buf = (hold.readline())
                buf = str(buf)
                buf = buf.strip("'b")
                buf = buf[:len(buf) - 2]
                species = buf.replace("GENOME: ",'')

                if species in self.organisms_to_files:
                    self.organisms_to_files[species][endo] = [file, file.replace(".cspr", "_repeats.db")]
                else:
                    self.organisms_to_files[species] = {}
                    self.organisms_to_files[species][endo] = [file, file.replace(".cspr", "_repeats.db")]

                if species in self.organisms_to_endos:
                    self.organisms_to_endos[species].append(endo)
                else:
                    self.organisms_to_endos[species] = [endo]
                    if self.orgChoice.findText(species) == -1:
                        self.orgChoice.addItem(species)

        #self.orgChoice.addItem("Custom Input Sequences")
        # auto fill the kegg search bar with the first choice in orgChoice
        if found == False:
            return False

        self.endoChoice.clear()
        self.endoChoice.addItems(self.organisms_to_endos[str(self.orgChoice.currentText())])
        self.orgChoice.currentIndexChanged.connect(self.changeEndos)


    def changeEndos(self):
        if self.orgChoice.currentText() != "Custom Input Sequences":
            self.Step2.setEnabled(True)
            self.endoChoice.setEnabled(True)
            self.seq_label.hide()
            self.radioButton_Gene.show()
            self.radioButton_Position.show()
            self.endoChoice.clear()
            self.endoChoice.addItems(self.organisms_to_endos[str(self.orgChoice.currentText())])
        else:
            self.Step2.setEnabled(False)
            self.endoChoice.clear()
            self.endoChoice.setEnabled(False)
            self.radioButton_Gene.hide()
            self.radioButton_Position.hide()
            self.seq_label.show()


    def change_directory(self):
        filed = QtWidgets.QFileDialog()
        mydir = QtWidgets.QFileDialog.getExistingDirectory(filed, "Open a folder...",
                                                           self.dbpath, QtWidgets.QFileDialog.ShowDirsOnly)

        if os.path.isdir(mydir) == False:
            #check if directory is a valid directory
            QtWidgets.QMessageBox.question(self, "Not a directory", "The directory you selected does not exist.",
                                           QtWidgets.QMessageBox.Ok)
            return


        #check if directory contains CSPR files
        found = False
        for file in os.listdir(mydir):
            if (file.find(".cspr") != -1):
                found = True
                break
        if (found == False):
            QtWidgets.QMessageBox.critical(self, "Directory is invalid!",
                                           "You must select a directory with CSPR Files!",
                                           QtWidgets.QMessageBox.Ok)
            return


        os.chdir(mydir)
        if platform.system() == "Windows":
            mydir = mydir.replace("/","\\")
        GlobalSettings.CSPR_DB = mydir
        #update dropdowns in main, MT, pop
        self.getData()

        GlobalSettings.MTWin.directory = mydir
        GlobalSettings.MTWin.get_data()
        GlobalSettings.pop_Analysis.get_data()
        self.fill_annotation_dropdown()


    # Tanner - added this function to allow the Tools->Multitargeting button to work
    # Function launches the multitargeting window and closing the current one
    def changeto_multitargeting(self):
        os.chdir(os.getcwd())
        GlobalSettings.MTWin.mwfg.moveCenter(GlobalSettings.MTWin.cp)  ##Center window
        GlobalSettings.MTWin.move(GlobalSettings.MTWin.mwfg.topLeft())  ##Center window
        GlobalSettings.MTWin.show()
        GlobalSettings.mainWindow.hide()


    def changeto_population_Analysis(self):
        GlobalSettings.pop_Analysis.mwfg.moveCenter(GlobalSettings.pop_Analysis.cp)  ##Center window
        GlobalSettings.pop_Analysis.move(GlobalSettings.pop_Analysis.mwfg.topLeft())  ##Center window
        GlobalSettings.pop_Analysis.launch()
        GlobalSettings.pop_Analysis.show()
        GlobalSettings.mainWindow.hide()


#    def add_org_popup(self):
#        info = "This functionality will allow users to use different organisms for off-target analysis in a future " \
#               "version of the software. If you need to run analysis on multiple organisms, please use the Population " \
#               "Analysis feature."
#        QtWidgets.QMessageBox.information(self, "Add Organism Information", info, QtWidgets.QMessageBox.Ok)


    def annotation_information(self):
        info = "Annotation files are used for searching for spacers on a gene/locus basis and can be selected here using either " \
               "NCBI databases or a local file."
        QtWidgets.QMessageBox.information(self, "Annotation Information", info, QtWidgets.QMessageBox.Ok)


    def open_ncbi_blast_web_page(self):
        webbrowser.open('https://blast.ncbi.nlm.nih.gov/Blast.cgi', new=2)


    def open_ncbi_web_page(self):
        webbrowser.open('https://www.ncbi.nlm.nih.gov/', new=2)


    def open_casper2_web_page(self):
        webbrowser.open('http://casper2.org/', new=2)


    def visit_repo_func(self):
        webbrowser.open('https://github.com/TrinhLab/CASPERapp')


    @QtCore.pyqtSlot()
    def view_results(self):
        self.Results.annotation_path = self.annotation_parser.annotationFileName ### Set annotation path
        self.hide()
        try:
            self.Results.endonucleaseBox.currentIndexChanged.disconnect()        
        except:
            pass
        # set Results endo combo box
        self.Results.endonucleaseBox.clear()

        # set GeneViewer to appropriate annotation file

        # set the results window endoChoice box menu
        # set the mainWindow's endoChoice first, and then loop through and set the rest of them
        self.Results.endonucleaseBox.addItem(self.endoChoice.currentText())
        for item in self.organisms_to_endos[str(self.orgChoice.currentText())]:
            if item != self.Results.endonucleaseBox.currentText():
                self.Results.endonucleaseBox.addItem(item)

        self.Results.mwfg.moveCenter(self.Results.cp)  ##Center window
        self.Results.move(self.Results.mwfg.topLeft())  ##Center window
        self.Results.endonucleaseBox.currentIndexChanged.connect(self.Results.changeEndonuclease)
        self.Results.load_gene_viewer()
        self.Results.get_endo_data()
        self.Results.show()


    # this function calls the closingWindow class.
    def closeEvent(self, event):
        self.closeFunction()
        event.accept()


    # this if the function that is called when the user closes the program entirely.
    # so far I only know of 4 spots that can do this
    #       1. mainWindow
    #       2. annotationsWindow
    #       3. Results
    #       4. Multitargetting
    def closeFunction(self):
        try:
            self.ncbi.close()
        except:
            print("no ncbi window to close")
        self.myClosingWindow.get_files()
        self.myClosingWindow.show()


    def close_app(self):
        try:
            self.ncbi.close()
        except:
            print("no ncbi window to close")

        self.closeFunction()
        self.close()


# ----------------------------------------------------------------------------------------------------- #
# =========================================================================================
# CLASS NAME: StartupWindow
# Inputs: Takes information from the main application window and displays the gRNA results
# Outputs: The display of the gRNA results search
# =========================================================================================


class StartupWindow(QtWidgets.QDialog):
    def __init__(self):
        super(StartupWindow, self).__init__()
        uic.loadUi(GlobalSettings.appdir + 'startupCASPER.ui', self)
        self.setWindowModality(2)  # sets the modality of the window to Application Modal
        self.setWindowIcon(QtGui.QIcon(GlobalSettings.appdir + "cas9image.png"))
        pixmap = QtGui.QPixmap(GlobalSettings.appdir + 'CASPER-logo.jpg')
        self.labelforart.setPixmap(pixmap)
        self.pushButton_2.setDefault(True)
        # Check to see the operating system you are on and change this in Global Settings:
        GlobalSettings.OPERATING_SYSTEM_ID = platform.system()
        self.info_path = os.getcwd()
        self.gdirectory = self.check_dir()
        GlobalSettings.CSPR_DB = self.gdirectory
        if platform.system() == "Windows":
            GlobalSettings.CSPR_DB = GlobalSettings.CSPR_DB.replace("/","\\")
        else:
            GlobalSettings.CSPR_DB = GlobalSettings.CSPR_DB.replace("\\","/")
        self.lineEdit.setText(self.gdirectory)

        self.pushButton_3.clicked.connect(self.changeDir)
        self.pushButton_2.clicked.connect(self.show_window)
        self.pushButton.clicked.connect(self.errormsgmulti)
        self.show()


    ####---FUNCTIONS TO RUN EACH BUTTON---####
    def changeDir(self):
        filed = QtWidgets.QFileDialog()
        mydir = QtWidgets.QFileDialog.getExistingDirectory(filed, "Open a folder...",
                                                           self.gdirectory, QtWidgets.QFileDialog.ShowDirsOnly)

        if (os.path.isdir(mydir) == False):
            QtWidgets.QMessageBox.question(self, "Not a directory", "The directory you selected does not exist.",
                                           QtWidgets.QMessageBox.Ok)
            return

        if platform.system() == "Windows":
            mydir = mydir.replace("/","\\")

        self.lineEdit.setText(mydir)
        self.gdirectory = mydir
        GlobalSettings.CSPR_DB = mydir

    #launch new genome
    def errormsgmulti(self):
        self.gdirectory = str(self.lineEdit.text())

        if (os.path.isdir(self.gdirectory)):
            os.chdir(self.gdirectory)

            # update dir in CASPERinfo
            self.re_write_dir()

            #make sure FNA and GBFF subdirectories are present
            subdirs = os.listdir(self.gdirectory)
            if "FNA" not in subdirs and os.path.isdir("FNA") == False:
                os.mkdir("FNA")
            if "GBFF" not in subdirs and os.path.isdir("GBFF") == False:
                os.mkdir("GBFF")

            #launch new genome
            GlobalSettings.mainWindow.launch_newGenome()

            self.close()
        else:
            QtWidgets.QMessageBox.question(self, "Not a directory", "The directory you selected does not exist.",
                                           QtWidgets.QMessageBox.Ok)


    def check_dir(self):
        cspr_info = open(GlobalSettings.appdir + "CASPERinfo", 'r+')
        cspr_info = cspr_info.read()
        lines = cspr_info.split('\n')
        dir = ""
        for item in lines:
            if 'DIRECTORY:' in item:
                dir = item
                break
        dir = dir.replace("DIRECTORY:", "")
        if platform.system() == "Windows":
            dir = dir.replace("/","\\")
        return dir

    def re_write_dir(self):
        cspr_info = open(GlobalSettings.appdir + "CASPERinfo", 'r+')
        cspr_info_text = cspr_info.read()
        cspr_info_text = cspr_info_text.split('\n')
        full_doc = ""
        for item in cspr_info_text:
            if 'DIRECTORY:' in item:
                line = item
                break

        line_final = "DIRECTORY:" + self.gdirectory
        for item in cspr_info_text:
            if item == line:
                full_doc = full_doc + "\n" + line_final
            else:
                full_doc = full_doc + "\n" + item
        full_doc = full_doc[1:]
        cspr_info.close()
        cspr_info = open(GlobalSettings.appdir + "CASPERinfo", 'w+')
        cspr_info.write(full_doc)

        cspr_info.close()

    #launch main
    def show_window(self):
        if (os.path.isdir(self.gdirectory) == False):
            QtWidgets.QMessageBox.question(self, "Not a directory", "The directory you selected does not exist.",
                                           QtWidgets.QMessageBox.Ok)
            return

        found = False
        for file in os.listdir(self.gdirectory):
            if (file.find(".cspr") != -1):
                found = True
                break

        if (found == False):
            QtWidgets.QMessageBox.critical(self, "Directory is invalid!",
                                           "You must select a directory with CSPR Files!",
                                           QtWidgets.QMessageBox.Ok)
            return

        self.gdirectory = str(self.lineEdit.text())
        if "Please select a directory that contains .cspr files" in self.gdirectory:
            QtWidgets.QMessageBox.question(self, "Must select directory", "You must select your directory.",
                                           QtWidgets.QMessageBox.Ok)
        elif (os.path.isdir(self.gdirectory)):

            os.chdir(self.gdirectory)
            found = GlobalSettings.mainWindow.getData()
            GlobalSettings.mainWindow.fill_annotation_dropdown()
            if found == False:
                QtWidgets.QMessageBox.question(self, "No .cspr files",
                                               "Please select a directory that contains cspr files.",
                                               QtWidgets.QMessageBox.Ok)
                return

            self.re_write_dir()

            #make sure FNA and GBFF subdirectories are present
            subdirs = os.listdir(self.gdirectory)
            if "FNA" not in subdirs and os.path.isdir("FNA") == False:
                os.mkdir("FNA")
            if "GBFF" not in subdirs and os.path.isdir("GBFF") == False:
                os.mkdir("GBFF")

            # Tanner - still setup data for MT
            GlobalSettings.MTWin.launch()

            GlobalSettings.mainWindow.show()

            self.close()
        else:
            QtWidgets.QMessageBox.question(self, "Not a directory", "The directory you selected does not exist.",
                                           QtWidgets.QMessageBox.Ok)


def main():
    if hasattr(sys, 'frozen'):
        GlobalSettings.appdir = sys.executable
        if platform.system() == 'Windows':
            GlobalSettings.appdir = GlobalSettings.appdir[:GlobalSettings.appdir.rfind("\\") + 1]
        else:
            GlobalSettings.appdir = GlobalSettings.appdir[:GlobalSettings.appdir.rfind("/") + 1]
    else:
        GlobalSettings.appdir = os.path.dirname(os.path.abspath(__file__))
        if platform.system() == 'Windows':
            GlobalSettings.appdir += '\\'
        else:
            GlobalSettings.appdir += '/'

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = Qt.QApplication(sys.argv)
    app.setOrganizationName("TrinhLab-UTK")
    app.setApplicationName("CASPER")
    startup = StartupWindow()
    GlobalSettings.mainWindow = CMainWindow(os.getcwd())
    GlobalSettings.MTWin = multitargeting.Multitargeting()
    GlobalSettings.pop_Analysis = populationAnalysis.Pop_Analysis()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
