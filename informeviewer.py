from kivy.uix.screenmanager import Screen


class InformeViewer(Screen):

    texto=""

    def mostrar(self,texto):

        self.texto=texto

        self.ids.lbl_informe.text=texto

    def exportar_pdf(self):

        print("Exportar PDF")

    def exportar_excel(self):

        print("Exportar Excel")