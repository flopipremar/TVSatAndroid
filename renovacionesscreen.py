from kivy.properties import ListProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.metrics import dp
from datetime import datetime
from util_db import stock_creditos
import calendar
from kivy.uix.popup import Popup

from db import get_conn


class RenovacionesScreen(Screen):

    usuarios = ListProperty([])
    usuarios_full = []

    def on_pre_enter(self):
        self.cargar_usuarios()
        self.limpiar()

    def cargar_usuarios(self):

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT usuario
            FROM usuarios
            WHERE activo=1
            ORDER BY usuario
        """)

        filas = cur.fetchall()

        conn.close()

        self.usuarios_full = [f[0] for f in filas]
        self.usuarios = self.usuarios_full.copy()

    def filtrar_usuarios(self, texto):

        texto = texto.lower()

        if texto == "":
            self.usuarios = self.usuarios_full.copy()
            return

        self.usuarios = [
            u for u in self.usuarios_full
            if texto in u.lower()
        ]

    def buscar_usuario(self, usuario):

        self.ids.contenedor_clientes.clear_widgets()
        self.usuario_actual = usuario
        
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.nombre,
                u.sistema,
                u.fecha_vencimiento
            FROM usuarios u
            JOIN clientes c
                ON c.id = u.cliente_id
            WHERE u.usuario = ?
            AND u.activo = 1
            ORDER BY c.nombre
        """, (usuario,))

        filas = cur.fetchall()

        conn.close()

        if not filas:
            return

        self.sistema_actual = filas[0][1]
        self.vencimiento_actual = filas[0][2]

        self.ids.lbl_sistema.text = self.sistema_actual
        self.ids.lbl_vencimiento.text = self.vencimiento_actual

        for fila in filas:

            self.ids.contenedor_clientes.add_widget(
                Label(
                    text=fila[0],
                    size_hint_y=None,
                    height=dp(35)
                )
            )

    def limpiar(self):

        self.ids.filtro_usuario.text = ""

        self.ids.usuario_spinner.text = "Seleccionar usuario"

        self.ids.lbl_sistema.text = "-"

        self.ids.lbl_vencimiento.text = "-"

        self.ids.contenedor_clientes.clear_widgets()

        self.usuarios = self.usuarios_full.copy()


    def renovar_usuario(self):

        if not hasattr(self, "usuario_actual"):
            self.popup("Error", "Seleccioná un usuario.")
            return

        nuevo_venc = self.calcular_proximo_vencimiento(
            self.vencimiento_actual
        )

        # Verificar que haya créditos disponibles
        if stock_creditos(self.sistema_actual) <= 0:
            self.popup(
                "Sin créditos",
                f"No quedan créditos disponibles para {self.sistema_actual}"
            )
            return

        nuevo_venc = self.calcular_proximo_vencimiento(
            self.vencimiento_actual
        )

        conn = get_conn()
        cur = conn.cursor()

        try:

            # Actualiza TODOS los clientes que usan ese usuario
            cur.execute("""
                UPDATE usuarios
                SET fecha_vencimiento=?
                WHERE usuario=?
                AND activo=1
            """,(nuevo_venc,self.usuario_actual))

            # Obtiene los registros de usuarios que fueron renovados
            cur.execute("""
                SELECT id
                FROM usuarios
                WHERE usuario = ?
                AND activo = 1
            """, (self.usuario_actual,))

            usuarios = cur.fetchall()

            from datetime import datetime

            fecha_hoy = datetime.now().strftime("%d/%m/%Y")

            # Guarda una renovación por cada registro de usuario
            for (usuario_id,) in usuarios:

                cur.execute("""
                    INSERT INTO renovaciones (
                        usuario_id,
                        fecha_renovacion,
                        fecha_vencimiento_anterior,
                        fecha_vencimiento_nuevo
                    )
                    VALUES (?,?,?,?)
                """, (
                    usuario_id,
                    fecha_hoy,
                    self.vencimiento_actual,
                    nuevo_venc
                ))

            # Registrar el consumo del crédito (un solo movimiento)
            cur.execute("""
                INSERT INTO movimientos_creditos (
                    fecha,
                    sistema,
                    tipo,
                    creditos,
                    usuario_id,
                    compra_id,
                    observacion
                )
                VALUES (?,?,?,?,?,?,?)
            """, (
                fecha_hoy,
                self.sistema_actual,
                "CONSUMO",
                -1,
                usuarios[0][0],      # toma el primer usuario_id
                None,
                f"Renovación de {self.usuario_actual}"
            ))

            conn.commit()

        finally:
            conn.close()

        self.buscar_usuario(self.usuario_actual)

        self.popup(
            "Éxito",
            f"Usuario renovado.\nNuevo vencimiento: {nuevo_venc}"
        )

    def calcular_proximo_vencimiento(self, fecha_actual_str):
        try:
            fecha_dt = datetime.strptime(fecha_actual_str, "%d/%m/%Y")

            mes = (fecha_dt.month % 12) + 1
            anio = fecha_dt.year + (1 if fecha_dt.month == 12 else 0)

            dia = min(
                fecha_dt.day,
                calendar.monthrange(anio, mes)[1]
            )

            return datetime(
                anio,
                mes,
                dia
            ).strftime("%d/%m/%Y")

        except:
            return fecha_actual_str
        
    def popup(self,titulo,texto):

        Popup(
            title=titulo,
            content=Label(text=texto),
            size_hint=(0.7,0.3)
        ).open()