# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 14:41:32 2026

@author: isahe
"""

# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# --- 1. FUNCIÓN DE FILTRADO ---
def filtrar_nombre(texto):
    # Quitamos medidas (30 ml, 50ml), símbolos y normalizamos
    texto = re.sub(r'\d+\s?ml', '', texto, flags=re.IGNORECASE)
    texto = texto.replace('®', '').replace('™', '').replace('...', '')
    return " ".join(texto.split()).lower()

# --- 2. FUNCIÓN DE CLASIFICACIÓN DETALLADA ---
def clasificar_maquillaje(ingredientes_raw):
    """Clasifica y detecta los componentes negativos específicos."""
    if not ingredientes_raw or "No se pudo" in ingredientes_raw or "Error" in ingredientes_raw:
        return "SIN DATOS", "❓", []
    
    # Lista de ingredientes críticos a vigilar 
    criticos = [
        "paraben", "formaldehyde", "triclosan", "phthalate",
        "petrolatum", "paraffinum","siloxane", "styrene",
        "peg-", "sulfate"
        ]
    
    texto = ingredientes_raw.lower()
    encontrados = [ing for ing in criticos if ing in texto]
    
    if len(encontrados) == 0:
        return "BUENO", "✅", []
    elif len(encontrados) <= 2:
        return "NO TAN BUENO", "⚠️", encontrados
    else:
        return "MALO", "❌", encontrados

options = webdriver.ChromeOptions()
options.add_argument('--start-maximized')
options.add_argument("--disable-notifications")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

todos_los_productos = []

try:

    # === FASE 1: DOUGLAS ===
    print("Iniciando extracción en Douglas...")
    driver.get("https://www.douglas.es/es")
    time.sleep(4)
    
    
    try:
        wait.until(EC.presence_of_element_located((By.ID, "usercentrics-root")))
        driver.execute_script('''
            const shadowHost = document.querySelector("#usercentrics-root");
            const btn = shadowHost.shadowRoot.querySelector('button[data-testid="uc-accept-all-button"]');
            if (btn) btn.click();
        ''')
        print("Cookies Douglas aceptadas correctamente.")
        
    except: pass

    # Búsqueda Douglas
    buscador_dg = wait.until(EC.presence_of_element_located((By.ID, "typeAhead-input")))
    buscador_dg.send_keys("colorete")
    buscador_dg.send_keys(Keys.ENTER)
    
    time.sleep(5)
    items_dg = driver.find_elements(By.CSS_SELECTOR, '[data-testid="product-tile"]')
    
    count_dg = 0
    idx = 0
    while count_dg < 10 and idx < len(items_dg):
        try:
            marca = items_dg[idx].find_element(By.CLASS_NAME, "top-brand").text.strip()
            nombre = items_dg[idx].find_element(By.CLASS_NAME, "brand-line").text.strip()
            
            if marca and nombre:
                todos_los_productos.append({
                    "tienda": "Douglas",
                    "marca": marca,
                    "busqueda_total": f"{marca} {filtrar_nombre(nombre)}"
                })
                print(f"Douglas OK: {marca}")
                count_dg += 1
        except:
            pass
        idx += 1


    # === FASE 2: PRIMOR ===
    print("\nIniciando extracción en Primor...")
    driver.get("https://www.primor.eu/")
    time.sleep(2)

    # Limpieza de capas Primor
    driver.execute_script("""
        const els = ['#onetrust-banner-sdk', '#INDshadowRootWrap'];
        els.forEach(id => { const el = document.querySelector(id); if(el) el.remove(); });
    """)

    # Búsqueda Primor
    buscador_pr = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-test="search-input"]')))
    driver.execute_script("arguments[0].click();", buscador_pr)
    buscador_pr.send_keys("colorete")
    buscador_pr.send_keys(Keys.ENTER)
    
    time.sleep(3)
    items_pr = driver.find_elements(By.CSS_SELECTOR, 'li[data-v-070eaadb]')
    
    count_pr = 0
    idx = 0
    while count_pr < 10 and idx < len(items_pr):
        try:
            marca = items_pr[idx].find_element(By.CSS_SELECTOR, 'h2[data-test="result-title"]').text.strip()
            nombre = items_pr[idx].find_element(By.CSS_SELECTOR, 'span.x-text2').text.strip()
            
            if marca and nombre:
                todos_los_productos.append({
                    "tienda": "Primor",
                    "marca": marca,
                    "busqueda_total": f"{marca} {filtrar_nombre(nombre)}"
                })
                print(f"Primor OK: {marca}")
                count_pr += 1
        except:
            pass
        idx += 1
        

    # === FASE 3: VALORACIONES EN AMAZON ===
    print("\n" + "="*50)
    print("INICIANDO FASE 3: BÚSQUEDA DE VALORACIONES EN AMAZON")
    print("="*50)

    productos_con_nota = []
    cookies_aceptadas_amazon = False 

    for prod in todos_los_productos:
        nombre_para_amazon = prod['busqueda_total']
        url_amazon = f"https://www.amazon.es/s?k={nombre_para_amazon.replace(' ', '+')}"
        
        try:
            driver.get(url_amazon)
            if not cookies_aceptadas_amazon:
                try:
                    btn_cookies_amz = wait.until(EC.element_to_be_clickable((By.ID, "sp-cc-accept")))
                    btn_cookies_amz.click()
                    cookies_aceptadas_amazon = True
                except:
                    cookies_aceptadas_amazon = True 

            

            try:
                primer_bloque = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]')
                ))
                
                nota_final = 0.0
                num_reviews = 0
                
                
                
                try:
                    elemento_nota = primer_bloque.find_element(By.CSS_SELECTOR, "span.a-size-small.a-color-base")
                    nota_final = float(elemento_nota.text.replace(',', '.'))
                except:
                    estrella_elem = primer_bloque.find_element(By.CSS_SELECTOR, "i.a-icon-star, span.a-icon-alt")
                    nota_texto = estrella_elem.get_attribute("aria-label") or estrella_elem.get_attribute("innerHTML")
                    match = re.search(r"(\d[.,]\d)", nota_texto)
                    if match:
                        nota_final = float(match.group(1).replace(',', '.'))


                try:
                    reviews_elem = primer_bloque.find_element(By.CSS_SELECTOR, 'span.s-underline-text')
                    texto_raw = reviews_elem.text.strip().upper() 
                    texto_limpio = texto_raw.replace('(', '').replace(')', '')
                    
                    if 'K' in texto_limpio:
                        numero = float(texto_limpio.replace('K', '').replace(',', '.'))
                        num_reviews = int(numero * 1000)
                    else:
                        num_reviews = int(re.sub(r'\D', '', texto_limpio))
                except:
                    num_reviews = 0
                    
            except:
                pass

            prod['puntuacion'] = nota_final
            prod['reviews'] = num_reviews
            productos_con_nota.append(prod)
            print(f"Amazon OK: {prod['marca']} | Nota: {nota_final} | Reseñas: {num_reviews}")

        except Exception as e:
            print(f"Error en Amazon para {nombre_para_amazon}: {e}")

    # Selección de los 10 mejores
    ganadores = sorted(productos_con_nota, key=lambda x: (x['puntuacion'], x['reviews']), reverse=True)[:10]
    
    

    # === FASE 4: INCI BEAUTY (EXTRACCIÓN Y CLASIFICACIÓN) ===
    print("\n" + "="*50)
    print("INICIANDO FASE 4: ANÁLISIS DE COMPOSICIÓN EN INCI BEAUTY")
    print("="*50)
    
    ganadores_finales = []
    vistos = set()
    for g in ganadores:
        busqueda = g.get('busqueda_total')
        if busqueda not in vistos:
            ganadores_finales.append(g)
            vistos.add(busqueda)
            
                      
    for g in ganadores_finales:
        try:
            print(f" -> Procesando: {g['busqueda_total']}...")
            
            # PASO 2: Búsqueda Refinada 
            # Reemplazamos espacios por %20 para que la URL sea perfecta
            busqueda_url = g['busqueda_total'].replace(' ', '%20')
            driver.get(f"https://incibeauty.com/es/search/k/{busqueda_url}")
            
            # PASO 3: Gestión de Cookies (Solo si aparecen)
            try:
                WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, "fc-button-label"))).click()
            except: pass

            # PASO 4: Cierre de Anuncio 'dismiss-button' 
            try:
                # Espera corta para no perder tiempo si no hay anuncio
                btn_cerrar = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, "dismiss-button")))
                btn_cerrar.click()
                print(" Anuncio cerrado.")
            except: pass
         
            
            item_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.color-inherit")))
            driver.execute_script("arguments[0].click();", item_link)
            
            
                # Extracción con tus fallbacks originales
            try:
                bloque_comp = wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Composición')]/following-sibling::*[1]")))
                raw_text = bloque_comp.text.strip()
                if len(raw_text) < 15:
                    bloque_comp = driver.find_element(By.XPATH, "//div[contains(@class, 'composition')] | //div[./h2[contains(text(), 'Composición')]]")
                    raw_text = bloque_comp.text.split('Composición')[-1].strip()
                
                if "(*)" in raw_text: raw_text = raw_text.split("(*)")[0]
                limpio = re.sub(r'\*+,\s?', '', raw_text)
                limpio = limpio.replace("(*)", "").strip()
                g['ingredientes'] = limpio
                print("Composición obtenida con éxito.")
                
            except Exception:
                try:
                    cuerpo_pagina = driver.find_element(By.TAG_NAME, "body").text
                    if "Composición" in cuerpo_pagina:
                        texto_extraido = cuerpo_pagina.split("Composición")[1].split("(*)")[0].strip()
                        g['ingredientes'] = re.sub(r'\*+,\s?', '', texto_extraido)
                        print("Composición obtenida vía Fallback.")
                    else: raise Exception()
                except:
                    g['ingredientes'] = "No se pudo localizar ingredientes."

            # Aplicar clasificación de ingredientes
            calidad, icono, culpables = clasificar_maquillaje(g['ingredientes'])
            g['calidad'] = calidad
            g['icono'] = icono
            g['culpables'] = culpables

        except Exception:
            print(f"Error procesando {g['busqueda_total']}")
            g['ingredientes'], g['calidad'], g['icono'], g['culpables'] = "Error, el producto no se ha encontrado en INCI", "ERROR, el producto no se ha encontrado en INCI", "❓", []

    # === REPORTE FINAL CONSOLIDADO ===
    print("="*50)
    print("REPORTE FINAL DE PRODUCTOS ANALIZADOS")
    print("="*50)
    for g in ganadores_finales:
        print(f"\n{g['icono']} PRODUCTO: {g['busqueda_total'].upper()}")
        print(f"   Valoración Amazon: {g.get('puntuacion', 'N/A')} ({g.get('reviews', '0')} reseñas)")
        print(f"   Veredicto Salud: {g.get('calidad')}")
        
        if g.get('culpables'):
            print(f"   COMPONENTES CRÍTICOS: {', '.join(g['culpables'])}")
            
        print(f"   COMPOSICIÓN COMPLETA: {g.get('ingredientes', 'No disponible')}")
        print("-" * 70)

finally:
    driver.quit()
    print("\nNavegador cerrado.")