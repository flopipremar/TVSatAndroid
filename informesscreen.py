from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from db import get_conn
from kivy.metrics import dp 
from datetime import datetime
from kivy.clock import Clock
from config import CONFIG
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
import pandas as pd  # <--- Agregá este import arriba
import os

class InformesScreen(Screen):
    
    # def reporte_vencimientos(self):
    #     hoy = datetime.now().date()
    #     conn = get_conn()
    #     cur = conn.cursor()
    #     # Solo traemos clientes activos
    #     cur.execute("SELECT nombre, fecha_vencimiento, importe FROM clientes WHERE activo = 1")
    #     clientes = cur.fetchall()
    #     conn.close()

    #     lista_proximos = []

    #     for c in clientes:
    #         try:
    #             # Convertimos el texto de la DB a objeto fecha
    #             f_venc = datetime.strptime(c[1], "%d/%m/%Y").date()
    #             # Calculamos la diferencia en días
    #             diff = (f_venc - hoy).days

    #             # FILTRO OPERATIVO: Solo hoy (0) y los próximos 3 días (1, 2, 3)
    #             if 0 <= diff <= 3:
    #                 # Usamos colores: Rojo para hoy, Azul para los que vienen
    #                 color = "ff5555" if diff == 0 else "55ccff"
    #                 aviso = "[b]VENCE HOY[/b]" if diff == 0 else f"Vence en {diff} días"
                    
    #                 linea = f"• [color={color}]{c[0]}[/color] (${c[2]:.0f}) - {aviso} ({c[1]})"
    #                 lista_proximos.append((diff, linea)) # Guardamos diff para ordenar
    #         except: 
    #             continue

    #     # Ordenamos para que los que vencen hoy aparezcan primero
    #     lista_proximos.sort(key=lambda x: x[0])

    #     # Construcción del texto para el Popup
    #     resumen = "[size=22][b]ALERTAS DE COBRO (PRÓXIMOS 3 DÍAS)[/b][/size]\n\n"
        
    #     if lista_proximos:
    #         resumen += "\n".join([item[1] for item in lista_proximos])
    #     else:
    #         resumen += "[i]No hay cobros pendientes para los próximos 3 días.[/i]"

    #     self.mostrar_popup("Vencimientos Inminentes", resumen)

    def mostrar_popup(self, titulo, texto):
        from kivy.uix.popup import Popup
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.label import Label
        from kivy.core.window import Window

        # 1. Creamos el ScrollView que permitirá el desplazamiento
        scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False, # Bloqueamos el movimiento horizontal
            do_scroll_y=True   # Activamos el movimiento vertical
        )

        # 2. Creamos el Label con el texto del informe
        # Es clave usar markup=True para que lea tus etiquetas de color [color=...] y negrita [b]
        contenido_texto = Label(
            text=texto,
            markup=True,
            size_hint_y=None,
            text_size=(Window.width * 0.7, None), # Ajusta el ancho al 70% de la ventana
            halign='left',
            valign='top'
        )
        
        # Este truco es obligatorio en Kivy para que el ScrollView sepa el alto real del texto
        contenido_texto.bind(texture_size=contenido_texto.setter('size'))

        # 3. Metemos el texto dentro del scroll
        scroll.add_widget(contenido_texto)

        # 4. Creamos y abrimos el Popup conteniendo el ScrollView
        popup = Popup(
            title=titulo,
            content=scroll,
            size_hint=(0.8, 0.8) # Ocupa el 80% de la pantalla
        )
        popup.open()

    def clientes_por_vendedor(self):
        from db import get_conn

        titulo = "LISTA DE CLIENTES POR VENDEDOR"
        
        conn = get_conn()
        cur = conn.cursor()

        # Consultamos todos los clientes activos agrupados por vendedor
        cur.execute("""
            SELECT
                COALESCE(v.nombre, 'Sin vendedor') as vendedor_nombre,
                c.nombre as cliente_nombre,
                c.fecha_vencimiento,
                c.importe
            FROM clientes c
            LEFT JOIN vendedores v
                ON c.vendedor_id = v.id
            WHERE
                c.activo = 1
            ORDER BY
                vendedor_nombre,
                c.nombre
        """)

        filas = cur.fetchall()
        conn.close()

        # ---------------------------------------------
        # ARMAMOS EL TEXTO DEL INFORME
        # ---------------------------------------------
        texto = f"[b][size=22]{titulo}[/size][/b]\n\n"

        if not filas:
            texto += "No hay clientes activos registrados en la base de datos."
        else:
            vendedor_actual = None
            contador_clientes = 0
            total_vendedor = 0

            for vendedor, cliente, vto, importe in filas:
                # Si cambia el vendedor, imprimimos el encabezado del nuevo grupo
                if vendedor != vendedor_actual:
                    if vendedor_actual is not None:
                        # Cerramos el total del vendedor anterior
                        texto += f"[b]Total clientes: {contador_clientes}  |  Cuota mensual: $ {total_vendedor:,.0f}[/b]\n\n"
                    
                    vendedor_actual = vendedor
                    contador_clientes = 0
                    total_vendedor = 0
                    
                    texto += f"[color=55ccff][b]{vendedor_actual.upper()}[/b][/color]\n"

                # Formateamos cada línea de cliente
                texto += f" • {cliente:<30} (Vto: {vto})   $ {importe:,.0f}\n"
                contador_clientes += 1
                total_vendedor += importe

            # Imprimimos el total del último vendedor de la lista
            texto += f"[b]Total clientes: {contador_clientes}  |  Cuota mensual: $ {total_vendedor:,.0f}[/b]\n"

        # Mostramos la lista completa usando tu popup con scroll
        self.mostrar_popup(titulo, texto)
    
    def reporte_creditos(self):

        conn = get_conn()
        cur = conn.cursor()

        sistemas = ["Impakto", "IPTV", "ItvOpen", "IKS81W"]

        texto = "[b][size=22]ESTADO DE CRÉDITOS[/size][/b]\n\n"

        for sistema in sistemas:

            # Comprados
            cur.execute("""
                SELECT COALESCE(SUM(creditos),0)
                FROM movimientos_creditos
                WHERE sistema=?
                AND tipo='COMPRA'
            """,(sistema,))

            comprados = cur.fetchone()[0]

            # Consumidos
            cur.execute("""
                SELECT ABS(COALESCE(SUM(creditos),0))
                FROM movimientos_creditos
                WHERE sistema=?
                AND tipo='CONSUMO'
            """,(sistema,))

            consumidos = cur.fetchone()[0]

            # Ajustes
            cur.execute("""
                SELECT COALESCE(SUM(creditos),0)
                FROM movimientos_creditos
                WHERE sistema=?
                AND tipo='AJUSTE'
            """,(sistema,))

            ajustes = cur.fetchone()[0]

            # Stock actual
            cur.execute("""
                SELECT COALESCE(SUM(creditos),0)
                FROM movimientos_creditos
                WHERE sistema=?
            """,(sistema,))

            stock = cur.fetchone()[0]

            color = "55ff55" if stock > 10 else "ffff55" if stock > 5 else "ff5555"

            texto += f"[color=55ccff][b]{sistema}[/b][/color]\n"
            texto += f"Comprados : {comprados}\n"
            texto += f"Consumidos: {consumidos}\n"
            texto += f"Ajustes   : {ajustes:+}\n"
            texto += f"[color={color}]Stock actual: {stock}[/color]\n\n"

        conn.close()

        self.mostrar_popup(
            "Stock de Créditos",
            texto
        )
        
    def reporte_usuarios_vencer(self):

        from datetime import datetime, timedelta

        hoy = datetime.now().date()
        limite = hoy + timedelta(days=5)

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.nombre,
                u.sistema,
                u.usuario,
                u.fecha_vencimiento

            FROM usuarios u

            JOIN clientes c
            ON c.id=u.cliente_id

            WHERE u.activo=1

            ORDER BY u.fecha_vencimiento
        """)

        filas = cur.fetchall()

        conn.close()

        texto = "[b][size=22]USUARIOS A VENCER[/size][/b]\n\n"

        encontrados = 0

        for nombre, sistema, usuario, fecha in filas:

            try:
                venc = datetime.strptime(
                    fecha,
                    "%d/%m/%Y"
                ).date()

            except:
                continue

            if hoy <= venc <= limite:

                encontrados += 1

                texto += (
                    f"[b]{fecha}[/b]\n"
                    f"Cliente : {nombre}\n"
                    f"Sistema : {sistema}\n"
                    f"Usuario : {usuario}\n\n"
                )

        if encontrados == 0:

            texto += "No hay usuarios a vencer en los próximos 5 días."

        self.mostrar_popup(
            "Usuarios a Vencer",
            texto
        )

    def reporte_clientes_pagar(self):

        from datetime import datetime, timedelta

        hoy = datetime.now().date()
        limite = hoy + timedelta(days=5)

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.nombre,
                c.telefono,
                c.fecha_vencimiento,
                c.importe,
                v.nombre

            FROM clientes c

            LEFT JOIN vendedores v
                ON c.vendedor_id = v.id

            WHERE c.activo = 1

            ORDER BY c.fecha_vencimiento
        """)

        filas = cur.fetchall()

        conn.close()

        texto = "[b][size=22]CLIENTES A PAGAR[/size][/b]\n\n"

        encontrados = 0

        for nombre, telefono, fecha, importe, vendedor in filas:

            try:
                pago = datetime.strptime(
                    fecha,
                    "%d/%m/%Y"
                ).date()

            except:
                continue

            if hoy <= pago <= limite:

                encontrados += 1

                texto += (
                    f"[b]{fecha}[/b]\n"
                    f"{nombre}\n"
                    f"Tel: {telefono}\n"
                    f"Importe: ${importe}\n"
                    f"Vendedor: {vendedor}\n\n"
                )

        if encontrados == 0:

            texto += "No hay clientes para cobrar en los próximos 5 días."

        self.mostrar_popup(
            "Clientes a Pagar",
            texto
        )

    def proyeccion(self, tipo):
        from datetime import datetime, timedelta
        from config import CONFIG

        hoy = datetime.now().date()

        # ---------------------------------------------
        # PERÍODO DEL INFORME (CORREGIDO A 7 Y 30 DÍAS)
        # ---------------------------------------------
        if tipo == "semanal":
            limite = hoy + timedelta(days=7)
            titulo = "PROYECCIÓN SEMANAL"
        else:
            limite = hoy + timedelta(days=30)
            titulo = "PROYECCIÓN MENSUAL"

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.nombre,
                c.fecha_vencimiento,
                c.importe,
                COALESCE(v.nombre, 'Sin vendedor')
            FROM clientes c
            LEFT JOIN vendedores v
                ON c.vendedor_id = v.id
            WHERE
                c.activo = 1
            ORDER BY
                v.nombre,
                c.fecha_vencimiento,
                c.nombre
        """)

        filas = cur.fetchall()
        conn.close()

        # ---------------------------------------------
        # ARMAMOS EL INFORME
        # ---------------------------------------------
        texto = (
            f"[b][size=22]{titulo}[/size][/b]\n"
            f"Desde {hoy.strftime('%d/%m/%Y')} "
            f"hasta {limite.strftime('%d/%m/%Y')}\n\n"
        )

        total_general = 0
        subtotales = {}

        for nombre, fecha_txt, importe, vendedor in filas:
            # Excluir cuentas internas
            if nombre == "Cuentas Nuestras":
                continue

            try:
                fecha = datetime.strptime(
                    fecha_txt,
                    "%d/%m/%Y"
                ).date()
            except:
                continue

            # Solo clientes dentro del período (desde hoy hasta el límite)
            if not (hoy <= fecha <= limite):
                continue

            if vendedor not in subtotales:
                subtotales[vendedor] = []

            subtotales[vendedor].append(
                (fecha, nombre, importe)
            )

            total_general += importe

        # ---------------------------------------------
        # MOSTRAR POR VENDEDOR
        # ---------------------------------------------
        if not subtotales:
            texto += "No hay clientes para cobrar en este período."
        else:
            for vendedor in sorted(subtotales.keys()):
                texto += (
                    f"[color=55ccff]"
                    f"[b]{vendedor.upper()}[/b]"
                    f"[/color]\n"
                )

                subtotal = 0
                # Orden por fecha
                clientes = sorted(subtotales[vendedor])

                for fecha, nombre, importe in clientes:
                    texto += (
                        f"{fecha.strftime('%d/%m')}  "
                        f"{nombre}  "
                        f"$ {importe:,.0f}\n"
                    )
                    subtotal += importe

                texto += (
                    f"[b]Subtotal {vendedor}: "
                    f"$ {subtotal:,.0f}[/b]\n\n"
                )

        texto += (
            "\n=========================\n"
            f"[size=20][b]TOTAL A RECAUDAR[/b][/size]\n"
            f"[size=22][color=55ff55]"
            f"$ {total_general:,.0f}"
            f"[/color][/size]"
        )

        self.mostrar_popup(titulo, texto)

    def consulta_cuentas_cliente(self):
        conn = get_conn()
        cur = conn.cursor()
        
        # Traemos la relación Cliente - Sistema - Usuario
        cur.execute("""
            SELECT c.nombre, u.sistema, u.usuario 
            FROM clientes c
            JOIN usuarios u ON c.id = u.cliente_id
            WHERE c.activo = 1 AND u.activo = 1
            ORDER BY u.sistema, c.nombre
        """)
        filas = cur.fetchall()
        conn.close()

        # Separamos los datos en dos diccionarios para organizarlos
        itv_lista = []
        impakto_lista = []

        for nombre, sistema, usuario in filas:
            linea = f"  • [b]{nombre[:18].ljust(18)}:[/b] {usuario}"
            if sistema == "ItvOpen":
                itv_lista.append(linea)
            else:
                impakto_lista.append(linea)

        # Construimos el texto final con dos columnas visuales
        resumen = "[size=24][b]DETALLE DE CUENTAS ACTIVAS[/b][/size]\n\n"

        # --- SECCIÓN ITVOPEN ---
        resumen += "[color=55ccff][size=20][u]COLUMNA ITVOPEN:[/u][/size][/color]\n"
        if itv_lista:
            resumen += "\n".join(itv_lista)
        else:
            resumen += "  No hay usuarios en ItvOpen"

        resumen += "\n\n" + "—" * 30 + "\n\n"

        # --- SECCIÓN IMPAKTO ---
        resumen += "[color=ffcc55][size=20][u]COLUMNA IMPAKTO:[/u][/size][/color]\n"
        if impakto_lista:
            resumen += "\n".join(impakto_lista)
        else:
            resumen += "  No hay usuarios en Impakto"

        resumen += f"\n\n[i]Total: {len(itv_lista)} ItvOpen | {len(impakto_lista)} Impakto[/i]"

        self.mostrar_popup("Cuentas por Plataforma", resumen)
    
    # def consulta_dispositivos_compartidos(self):
    #     from kivy.uix.gridlayout import GridLayout # Asegurá este import arriba
        
    #     conn = get_conn()
    #     cur = conn.cursor()
    #     # Traemos todas las cuentas activas de Impakto
    #     cur.execute("""
    #         SELECT u.usuario, c.nombre 
    #         FROM usuarios u
    #         JOIN clientes c ON u.cliente_id = c.id
    #         WHERE u.activo = 1 AND u.sistema = 'Impakto'
    #         ORDER BY u.usuario
    #     """)
    #     filas = cur.fetchall()
    #     conn.close()

    #     # Agrupamos por cuenta: { 'cuenta1': ['Cli1', 'Cli2'], ... }
    #     cuentas = {}
    #     for usu, cliente in filas:
    #         if usu not in cuentas:
    #             cuentas[usu] = []
    #         cuentas[usu].append(cliente)

    #     # --- CREAMOS LA ESTRUCTURA VISUAL ---
    #     scroll = ScrollView(do_scroll_x=True) # Permitimos scroll lateral si los nombres son largos
        
    #     # Grid de 4 columnas: Cuenta | Cliente 1 | Cliente 2 | Cliente 3
    #     tabla = GridLayout(cols=4, size_hint_y=None, spacing=dp(5), padding=dp(10))
    #     tabla.bind(minimum_height=tabla.setter('height'))

    #     # Encabezados de la tabla
    #     encabezados = ["CUENTA", "CLIENTE 1", "CLIENTE 2", "CLIENTE 3"]
    #     for h in encabezados:
    #         tabla.add_widget(Label(text=f"[b]{h}[/b]", markup=True, size_hint_y=None, height=dp(40), color=(0.7, 0.7, 1, 1)))

    #     # Llenamos las filas
    #     for usu, clientes in cuentas.items():
    #         # Columna 1: Nombre de la cuenta (en celeste)
    #         tabla.add_widget(Label(text=usu, size_hint_y=None, height=dp(35), color=(0.3, 0.8, 1, 1)))
            
    #         # Columnas 2, 3 y 4: Los clientes (o vacío si no hay)
    #         for i in range(3):
    #             nombre_cli = clientes[i] if i < len(clientes) else "-"
    #             tabla.add_widget(Label(text=nombre_cli, size_hint_y=None, height=dp(35)))

    #     scroll.add_widget(tabla)
    #     Popup(title="Cuentas Impakto - Distribución de Clientes", content=scroll, size_hint=(0.95, 0.8)).open()
    
    def reporte_caja(self):
        conn = get_conn()
        cur = conn.cursor()
        
        # 1. RECAUDACIÓN (Lo que COBRAS): Suma de importes de clientes activos
        cur.execute("SELECT SUM(importe) FROM clientes WHERE activo = 1")
        total_recaudado = cur.fetchone()[0] or 0
        
        # 2. COSTOS (Lo que PAGAS): Contamos nombres de USUARIOS ÚNICOS por sistema
        cur.execute("""
            SELECT sistema, COUNT(DISTINCT usuario) 
            FROM usuarios 
            WHERE activo = 1 
            GROUP BY sistema
        """)
        consumo_real = {fila[0]: fila[1] for fila in cur.fetchall()}
        conn.close()

        # Precios de costo por crédito (único) - EDITÁ EL DE IPTV ACÁ
        COSTOS = {"ItvOpen": 550, "Impakto": 1500, "IPTV": 550}

        # --- CÁLCULOS ---
        cant_itv = consumo_real.get("ItvOpen", 0)
        cant_imp = consumo_real.get("Impakto", 0)
        cant_iptv = consumo_real.get("IPTV", 0) # <--- Nuevo
        
        gasto_itv = cant_itv * COSTOS["ItvOpen"]
        gasto_imp = cant_imp * COSTOS["Impakto"]
        gasto_iptv = cant_iptv * COSTOS["IPTV"] # <--- Nuevo
        
        total_costos = gasto_itv + gasto_imp + gasto_iptv
        ganancia_neta = total_recaudado - total_costos

        # --- CONSTRUCCIÓN DEL INFORME ---
        texto = "[b][size=22]BALANCE FINANCIERO REAL[/size][/b]\n\n"
        
        # Bloque ItvOpen
        texto += "[color=55ccff][b][u]SISTEMA ITVOPEN:[/u][/b][/color]\n"
        texto += f"• Créditos Únicos: {cant_itv}\n"
        texto += f"• Costo Panel: [color=ff5555]$ {gasto_itv:,.2f}[/color]\n\n"

        # Bloque Impakto
        texto += "[color=ffcc55][b][u]SISTEMA IMPAKTO:[/u][/b][/color]\n"
        texto += f"• Créditos Únicos: {cant_imp}\n"
        texto += f"• Costo Panel: [color=ff5555]$ {gasto_imp:,.2f}[/color]\n\n"

        # Bloque IPTV (Nuevo)
        texto += "[color=ff55ff][b][u]SISTEMA IPTV:[/u][/b][/color]\n"
        texto += f"• Créditos Únicos: {cant_iptv}\n"
        texto += f"• Costo Panel: [color=ff5555]$ {gasto_iptv:,.2f}[/color]\n\n"

        texto += "________________________________\n"
        texto += f"\n[b]RECAUDACIÓN BRUTA (Clientes): [color=55ff55]$ {total_recaudado:,.2f}[/color][/b]\n"
        texto += f"[b]GASTOS TOTALES (Paneles):    [color=ff5555]$ {total_costos:,.2f}[/color][/b]\n"
        texto += f"[size=24][b]GANANCIA NETA: [color=ffff55]$ {ganancia_neta:,.2f}[/color][/b][/size]\n"
        texto += f"\n[i]Resumen: Estás usando {cant_itv + cant_imp + cant_iptv} créditos reales.[/i]"

        self.mostrar_popup("Recaudación Mensual", texto)

    def consulta_pagos_global(self):
        """Muestra los últimos 30 pagos registrados en todo el sistema"""
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.nombre, p.fecha_pago, p.mes_correspondiente, p.importe_pagado 
            FROM pagos p 
            JOIN clientes c ON p.cliente_id = c.id 
            ORDER BY p.id DESC LIMIT 30
        """)
        pagos = cur.fetchall()
        conn.close()

        resumen = "[b][size=20]HISTORIAL RECIENTE DE PAGOS[/size][/b]\n\n"
        if not pagos:
            resumen += "No hay pagos registrados aún."
        else:
            for p in pagos:
                # p[0]=Nombre, p[1]=Fecha, p[2]=Mes cubierto, p[3]=Importe
                resumen += f"[color=55ff55]• {p[1]}[/color] | [b]{p[0]}[/b]\n"
                resumen += f"  Cubre: {p[2]} | [u]Recaudado: ${p[3]:,.2f}[/u]\n\n"

        self.mostrar_popup("Global de Pagos", resumen)
    
    def reporte_clientes_por_cantidad_impakto(self):
        conn = get_conn()
        cur = conn.cursor()
        
        # Agrupamos por cliente: contamos sus usuarios Impakto y sumamos lo que paga el cliente
        cur.execute("""
            SELECT c.nombre, COUNT(u.id) as cant, c.importe 
            FROM clientes c
            JOIN usuarios u ON c.id = u.cliente_id
            WHERE u.activo = 1 AND u.sistema = 'Impakto' AND c.activo = 1
            GROUP BY c.id
            ORDER BY cant DESC, c.nombre ASC
        """)
        filas = cur.fetchall()
        conn.close()

        # Estructura para organizar datos y dinero
        # { cant: { 'nombres': [], 'dinero': 0.0 } }
        categorias = {
            3: {'nombres': [], 'dinero': 0.0},
            2: {'nombres': [], 'dinero': 0.0},
            1: {'nombres': [], 'dinero': 0.0}
        }

        total_general = 0.0

        for nombre, cant, importe in filas:
            if cant in categorias:
                categorias[cant]['nombres'].append(nombre)
                categorias[cant]['dinero'] += importe
                total_general += importe
            elif cant > 3:
                # Caso especial por si alguien tiene más del límite estándar
                if "Más de 3" not in categorias: 
                    categorias["Más de 3"] = {'nombres': [], 'dinero': 0.0}
                categorias["Más de 3"]['nombres'].append(f"{nombre} ({cant})")
                categorias["Más de 3"]['dinero'] += importe
                total_general += importe

        # Construcción del informe
        texto = "[b][size=24]RECAUDACIÓN IMPAKTO POR CATEGORÍA[/size][/b]\n\n"
        
        # Ordenamos las llaves para que salgan 3, 2, 1
        claves_ordenadas = sorted([k for k in categorias.keys() if isinstance(k, int)], reverse=True)
        if "Más de 3" in categorias: claves_ordenadas.insert(0, "Más de 3")

        for num in claves_ordenadas:
            color = "55ff55" if num == 3 else "ffff55" if num == 2 else "55ccff"
            datos = categorias[num]
            cant_cli = len(datos['nombres'])
            recaudado = datos['dinero']
            
            # Encabezado de categoría con dinero
            texto += f"[color={color}][b][u]{num} DISPOSITIVOS[/u][/b][/color]\n"
            texto += f"• Clientes: {cant_cli}\n"
            texto += f"• [b]Total Recaudado: $ {recaudado:,.2f}[/b]\n"
            
            if cant_cli > 0:
                texto += f"  • {chr(10)}  • ".join(datos['nombres'])
            else:
                texto += "  (Sin clientes)"
            texto += "\n\n"

        texto += "________________________________\n"
        texto += f"\n[b][size=22]TOTAL RECAUDADO GRUPO: [color=55ff55]$ {total_general:,.2f}[/color][/size][/b]"

        self.mostrar_popup("Recaudación Impakto", texto)

    def informe_activos(self):
        # Aquí calcularemos cuánto dinero deberías cobrar este mes
        self.mostrar_popup("Caja", "Función en desarrollo...")

    def exportar_excel_completo(self):
        try:
            conn = get_conn()
            # Traemos una sábana de datos completa y limpia
            query = """
                SELECT 
                    c.nombre AS Cliente, 
                    c.telefono AS Telefono, 
                    u.sistema AS Sistema, 
                    u.usuario AS Cuenta_Usuario, 
                    c.fecha_vencimiento AS Vencimiento,
                    c.importe AS Cuota_Mensual
                FROM clientes c
                LEFT JOIN usuarios u ON c.id = u.cliente_id
                WHERE c.activo = 1
                ORDER BY c.nombre ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                self.mostrar_popup("Error", "No hay datos para exportar.")
                return

            # Nombre del archivo con la fecha de hoy para no pisar el anterior
            fecha_str = datetime.now().strftime("%d-%m-%Y")
            nombre_archivo = f"Gestion_TV_Sat_{fecha_str}.xlsx"
            
            # Guardamos el Excel
            df.to_excel(nombre_archivo, index=False)
            
            # Obtenemos la ruta completa para avisar dónde quedó
            ruta_completa = os.path.abspath(nombre_archivo)
            self.mostrar_popup("Exportación Exitosa", 
                               f"Archivo creado:\n[b]{nombre_archivo}[/b]\n\nEn la carpeta:\n[i]{os.path.dirname(ruta_completa)}[/i]")
            
        except Exception as e:
            self.popup("Error", f"No se pudo exportar: {e}")

    def consulta_compartidos_por_sistema(self, sistema_nombre):
        from kivy.uix.gridlayout import GridLayout

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT u.usuario, c.nombre
            FROM usuarios u
            JOIN clientes c ON u.cliente_id = c.id
            WHERE u.activo = 1 AND u.sistema = ?
            ORDER BY u.usuario
        """, (sistema_nombre,))

        filas = cur.fetchall()
        conn.close()

        if not filas:
            self.mostrar_popup(f"Consulta {sistema_nombre}", f"No hay cuentas cargadas en {sistema_nombre}")
            return

        cuentas = {}
        for usu, cliente in filas:
            cuentas.setdefault(usu, []).append(cliente)

        layout = BoxLayout(
            orientation="vertical",
            spacing=dp(5),
            padding=dp(5)
        )

        filtro = TextInput(
            hint_text="Buscar usuario...",
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )

        scroll = ScrollView(do_scroll_x=True)

        tabla = GridLayout(
            cols=4,
            size_hint_y=None,
            spacing=dp(5),
            padding=dp(10)
        )
        tabla.bind(minimum_height=tabla.setter("height"))

        def llenar_tabla(texto=""):
            tabla.clear_widgets()

            headers = ["CUENTA", "CLIENTE 1", "CLIENTE 2", "CLIENTE 3"]
            for h in headers:
                tabla.add_widget(Label(
                    text=f"[b]{h}[/b]",
                    markup=True,
                    size_hint_y=None,
                    height=dp(40),
                    color=(0.7, 0.7, 1, 1)
                ))

            texto = texto.lower()

            for usu, clientes in cuentas.items():
                if texto and texto not in usu.lower():
                    continue

                tabla.add_widget(Label(
                    text=usu,
                    size_hint_y=None,
                    height=dp(35),
                    color=(0.3, 0.8, 1, 1)
                ))

                for i in range(3):
                    nombre_cli = clientes[i] if i < len(clientes) else "-"
                    tabla.add_widget(Label(
                        text=nombre_cli,
                        size_hint_y=None,
                        height=dp(35)
                    ))

        llenar_tabla()

        filtro.bind(text=lambda instancia, valor: llenar_tabla(valor))

        scroll.add_widget(tabla)

        layout.add_widget(filtro)
        layout.add_widget(scroll)

        popup = Popup(
            title=f"Distribución de Clientes - {sistema_nombre}",
            content=layout,
            size_hint=(0.95, 0.8)
        )

        popup.bind(
            on_open=lambda *args: Clock.schedule_once(
                lambda dt: setattr(filtro, "focus", True), 0.1
            )
        )

        popup.open()

    # --- ESTAS SON LAS QUE LLAMARÁS DESDE EL .KV ---
    def consulta_impakto(self):
        self.consulta_compartidos_por_sistema("Impakto")

    def consulta_iptv(self):
        self.consulta_compartidos_por_sistema("IPTV")
    
    def popup(self, titulo, texto):
        # Función auxiliar por si no hereda mostrar_popup
        Popup(title=titulo, content=Label(text=texto), size_hint=(0.8, 0.4)).open()