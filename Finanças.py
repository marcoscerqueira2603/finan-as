import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openpyxl import load_workbook
import gspread
from google.auth.transport.requests import Request
from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials
from datetime import datetime, date
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import psycopg2
from dateutil.relativedelta import relativedelta

st.set_page_config(
    page_title="Finanças",
    layout="wide"
)

st.title('Página de Organização Financeira')

template_dash = "plotly_white"
bg_color_dash = "rgba(0,0,0,0)"

# Cores: rosa, rosa forte, vermelho, roxo, azul, azul claro, laranja, amarelo claro, preto acizentado
# "#f7a48b", "#fd0a60", "#fb4848", "#b88f93", "#44749d", "#bfe4cd", "#fa8331", "#f5f7bd", "#3d423c"

load_dotenv()

# Configuração da conexão
conn = st.connection("postgresql", type="sql")

def consultar_db(query):
    """
    Consulta ao banco de dados usando st.connection.
    Retorna um DataFrame com os resultados.
    """
    try:
        # Realiza a consulta e retorna um DataFrame
        df = conn.query(query, ttl="10m")  # Cache de 10 minutos
        return df

    except Exception as e:
        st.write(f"Erro ao consultar o banco de dados: {e}")
        return None

# Função para adicionar dados

SERVICE_ACCOUNT_FILE = "chave_api.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Inicializar a variável `creds` como None
creds = None

# Verificar se existe um token salvo (token.json), senão gerar novas credenciais
if os.path.exists('token.json'):
    try:
        creds = credentials.Credentials.from_authorized_user_file('token.json', SCOPES)
    except exceptions.GoogleAuthError as e:
        st.error(f"Erro ao carregar o token: {e}")

# Se não existir o token ou as credenciais estiverem expiradas, renovar ou criar novas
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        # Usar o arquivo de chave da conta de serviço para obter as credenciais
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    
    # Salvar o token atualizado para uso futuro
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

# Autenticando o cliente gspread com as credenciais
client = gspread.authorize(creds)

# Função para carregar dados da planilha
@st.cache_data(ttl=180)
def load_data_from_sheet(sheet_url):
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.get_worksheet(0)  # Assume que estamos acessando a primeira aba
    data = worksheet.get_all_records()  # Pega todos os dados como uma lista de dicionários
    return pd.DataFrame(data)



# Carregamento dos dados
debito = load_data_from_sheet(st.secrets["url_extrato_debito"])
credito = load_data_from_sheet(st.secrets["url_extrato_credito"])
vr = load_data_from_sheet(st.secrets["url_extrato_vr"])
receita = load_data_from_sheet(st.secrets["url_extrato_receitas"])
fixos = load_data_from_sheet(st.secrets["url_extrato_fixos"])
orcamento_mensal = load_data_from_sheet(st.secrets["url_orcamento_mensal"])
investimentos = load_data_from_sheet(st.secrets["url_investimento"])
emprestimos = load_data_from_sheet(st.secrets["url_emprestimos"])
orcamento_mensal = load_data_from_sheet(st.secrets["url_orcamento"])




tab1, tab2 = st.tabs(['Adicionar dados','Visualização'])

with tab1:

    with st.expander('Débito'):
        st.title('Débito')

        #adicionando dados relativos a aba de débito: incluem a data, a classificação, o valor, a descrição
        novos_debitos = []


        with st.form('form débito'):
            # Campos para inserir as informações do débito
            debito_mes_ref = st.selectbox('Selecione o mês referência:', 
                                        ['01_2024','02_2024','03_2024','04_2024','05_2024','06_2024','07_2024',
                                        '08_2024','09_2024','10_2024','11_2024','12_2024'], key='class-mesref_debito')

            debito_data = st.text_input('Insirir Data', key="inserir-data-debito")
            debito_descricao = st.text_input('Insirir Descrição', key="inserir-descricao-debito")

            debito_classificacao = st.selectbox('Selecione o tipo:', 
                                            ['Necessidade', 'Lazer - Corinthians', 'Lazer - Outros', 'Lazer - Comida', 
                                                'Comida', 'Aplicativo de Transporte', 'Outros'], key='class-debito')

            debito_valor = st.text_input('Insirir Valor', key="inserir-valor-debito")
            debito_compracredito = st.selectbox('Selecione o tipo:', 
                                            ['Não', 'Sim, com pagamento', 'Sim, sem pagamento'], key='compra-credito-debito')

            # Verificação de valor (caso esteja vazio, coloca 1.0 como padrão)
            if debito_valor == "":
                debito_valor = 1.0
            else:
                debito_valor = float(debito_valor)

            # Definindo data padrão caso o campo esteja vazio
            if debito_data == "":
                debito_data = "08/02/2000"
            
            # Botão de envio do formulário
            submit_button = st.form_submit_button("Adicionar Débito")

            if submit_button:
                with conn.session as session:
                    # Declarar a query como um texto SQL explícito
                    query = text("""
                        INSERT INTO financas.debito
                        (id_mes, data, classificacao, descricao, debito_compra_credito, valor)
                        VALUES (:id_mes, :data, :classificacao, :descricao, :debito_compra_credito, :valor);
                    """)
                    # Executar a query
                    session.execute(query, {
                        "id_mes": debito_mes_ref,
                        "data": debito_data,
                        "classificacao": debito_classificacao,
                        "descricao": debito_descricao,
                        "debito_compra_credito": debito_compracredito,
                        "valor": debito_valor
                    })
                    # Confirmar as alterações
                    session.commit()
                    st.success("Débito adicionado com sucesso!")

                # Adiciona o novo débito à lista de débitos
                novo_debito = [debito_mes_ref, debito_data, debito_classificacao, debito_descricao, debito_compracredito, debito_valor]
                novos_debitos.append(novo_debito)




        if novos_debitos:
            novos_debitos_df = pd.DataFrame(novos_debitos, columns=debito.columns)
            worksheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1lEIcy7vjH-X7U1t-toxC6V-ps39f6WQw2mruzTfx1VE/edit#gid=0').get_worksheet(0)
            
            # Obter o número de linhas existentes na planilha
            num_rows = len(worksheet.get_all_values())
            
            # Inserir os dados nas linhas subsequentes
            values_to_insert = novos_debitos_df.values.tolist()
            worksheet.insert_rows(values_to_insert, num_rows + 1) 

    with st.expander('Crédito'):

        st.title('Crédito')

        credito_parcelas =  st.number_input('Inserir Parcelas', value=1)
        meses_disponiveis = ['01_2024', '02_2024', '03_2024', '04_2024', '05_2024', '06_2024', '07_2024', '08_2024','09_2024','10_2024','11_2024','12_2024']
        credito_mes_parcela1 = st.selectbox('Selecione o mês inicial',  meses_disponiveis) 
        credito_valor = st.text_input('Insirir Valor Crédito', key = 'insirir-valor-credito')
        credito_descrição =  st.text_input('Insirir Descrição', key = 'insirir-descricao-credito')
        credito_classificacao = st.selectbox('Selecione o tipo:', ['Faturas 2023','Presente Pitica','Presentes - Família','Lazer','Roupas','Compras Minhas','Outros'], key='class-credito')
        credito_cartao = st.selectbox('Selecione o cartão:', ['Inter','Nubank','C6','Renner'], key='cartao-credito')


        if credito_valor == "":
            credito_valor = 100.0
        else:
            credito_valor = credito_valor

        credito_valor = float(credito_valor)

        valor_parcela = round(credito_valor / credito_parcelas, 2)



        novos_creditos = []  # Inicializa a lista antes de usá-la

        # Exibir formulário no Streamlit
        with st.form('form credito'):
            if st.form_submit_button('Adicionar Gasto Crédito'):
                # Criação das parcelas dentro do formulário
                mes_inicial = datetime.strptime(credito_mes_parcela1, "%m_%Y")
                for i in range(int(credito_parcelas)):
                    id_mes = mes_inicial.strftime("%m_%Y")
                    novo_credito = [id_mes, credito_cartao, credito_descrição, credito_classificacao, valor_parcela]
                    novos_creditos.append(novo_credito)

                    # Inserir no banco de dados
                    query_add_credito = """
                        INSERT INTO financas.credito(id_mes, credito_cartao, descricao, classificacao, valor)
                        VALUES (%s, %s, %s, %s, %s);
                    """
                    adicionar_dados(query_add_credito, novo_credito)  # Inserir um por vez

                    # Avançar para o próximo mês
                    mes_inicial += relativedelta(months=1)
        
        if novos_creditos:
            novos_creditos_df = pd.DataFrame(novos_creditos, columns=credito.columns)
            worksheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1xU7NwhHQkMGcF742y-tj9MjuK7XYnNhVt9r8dV60ofc/edit#gid=0').get_worksheet(0)
            
            # Obter o número de linhas existentes na planilha
            num_rows = len(worksheet.get_all_values())
            
            # Inserir os dados nas linhas subsequentes
            values_to_insert = novos_creditos_df.values.tolist()
            worksheet.insert_rows(values_to_insert, num_rows + 1) 
            
    with st.expander("Receita"): 
        st.title("Receita")
        
        receita_data = st.text_input('Insirir Data',key = 'insirir-data-receita ')
        receita_id_mes = st.selectbox('Selecione o mês referência:', ['01_2024','02_2024','03_2024','04_2024','05_2024','06_2024','07_2024','08_2024','09_2024','10_2024','11_2024','12_2024'], key='class-mesref_receita')
        if receita_data  == "":
            receita_data = "08/02/2000"
        else:
            receita_data = receita_data    

        
        receita_descrição =  st.text_input('Insirir Descrição', key = 'insirir-descricao-receita')
        receita_classificacao = st.selectbox('Selecione o tipo:', ['Salário','Bônus','13º','Cartola','Apostas','Investimentos','Outros'], key='class-receita')

        receita_valor = st.text_input('Insirir Valor', key = 'insirir-valor-receita')

        if receita_valor == "":
            receita_valor = 1.0
        else:
            receita_valor = receita_valor

        receita_valor = float(receita_valor)

        query_add_receita = """
                    INSERT INTO financas.receita(id_mes, data, classificacao,descricao,  valor)
                    VALUES (%s, %s, %s, %s, %s);
                    """
        novos_receitas = []

        with st.form('form receita'):
            if st.form_submit_button('Adicionar Receitas'):
                novo_receita = [receita_id_mes, receita_data,  receita_classificacao, receita_descrição, receita_valor]
                novos_receitas.append(novo_receita)
                adicionar_dados(query_add_receita,novo_receita)
                st.write("Operação totalmente concluída.")    

        if novos_receitas:
            novos_receitas_df = pd.DataFrame(novos_receitas, columns=receita.columns)
            worksheet = client.open_by_url('https://docs.google.com/spreadsheets/d/11diab8Ytz3q9wN_ZbxWw60DBH5ydBUb152pIhmC0Etw/edit#gid=0').get_worksheet(0)
            
            # Obter o número de linhas existentes na planilha
            num_rows = len(worksheet.get_all_values())
            
            # Inserir os dados nas linhas subsequentes
            values_to_insert = novos_receitas_df.values.tolist()
            worksheet.insert_rows(values_to_insert, num_rows + 1) 
            
    with st.expander('Fixos'):
        st.title('Fixos')

        fixos_mes_ref = st.selectbox('Selecione o mês referência:', ['01_2024','02_2024','03_2024','04_2024','05_2024',
                                                                        '06_2024','07_2024','08_2024','09_2024','10_2024',
                                                                        '11_2024','12_2024'], key='class-mesref_fixos')
        
        fixos_data = st.text_input('Insirir Data', key = "inserir-data-fixos")
        fixos_descrição =  st.text_input('Insirir Descrição', key = "inserir-descricao-fixos")

        fixos_classificacao = st.selectbox('Selecione o tipo:', ['Casa', 'Fiel Torcedor', 'Cabelo', 'Internet Celular', 'Spotify','Passagem', 'Seguro Celular','Streaming','Tembici - Itaú',], key='class-fixos')
        fixos_valor = st.text_input('Insirir Valor', key = "inserir-valor-fixos")

        if fixos_valor == "":
            fixos_valor = 1.0
        else:
            fixos_valor = fixos_valor

        fixos_valor = float(fixos_valor)

        if fixos_data  == "":
            fixos_data = "08/02/2000"
        else:
            fixos_data = fixos_data    

        fixos_algumcredito =  st.selectbox('Gasto em algum crédito?:', ['', 'Nubank','Inter' ], key='class-algumcredito_fixos')


        query_add_fixo = """
                    INSERT INTO financas.fixo (id_mes, data, classificacao, valor, descricao, fixo_compra_credito)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """

        novos_fixos = []
        with st.form('form fixos'):
            if st.form_submit_button('Adicionar Fixos'):
                novos_fixo = [ fixos_mes_ref, fixos_data,fixos_classificacao, fixos_valor , fixos_descrição ,fixos_algumcredito]
                novos_fixos.append(novos_fixo)
                adicionar_dados(query_add_fixo,novos_fixo)
                st.write("Operação totalmente concluída.")    

        
        if novos_fixos:
            novos_fixos_df = pd.DataFrame(novos_fixos, columns=fixos.columns)
            worksheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1AxG0j2qOZ9e1MRUCD20Jhd0roqPcZ8lcQPBhlIqwwGs/edit#gid=0').get_worksheet(0)
            
            # Obter o número de linhas existentes na planilha
            num_rows = len(worksheet.get_all_values())
            
            # Inserir os dados nas linhas subsequentes
            values_to_insert = novos_fixos_df.values.tolist()
            worksheet.insert_rows(values_to_insert, num_rows + 1) 

    with st.expander('Investimentos'):
        st.title('Investimentos')

        investimentos_mes_ref = st.selectbox('Selecione o mês referência:', ['01_2024','02_2024','03_2024','04_2024','05_2024',
                                                                        '06_2024','07_2024','08_2024','09_2024','10_2024',
                                                                        '11_2024','12_2024'], key='class-mesref_investimentos')
        
        investimentos_descrição =  st.text_input('Insirir Descrição', key = "inserir-descricao-investimentos")
        investimentos_tipo =  st.text_input('Insirir Tipo Investimentos', key = "inserir-tipo-investimentos")
        investimentos_data = st.text_input('Insirir Data', key = "inserir-data-investimentos")
        investimentos_valor = st.text_input('Insirir Valor', key = "inserir-valor-investimentos")

        if investimentos_valor == "":
            investimentos_valor = 1.0
        else:
            investimentos_valor = investimentos_valor

        investimentos_valor = float(investimentos_valor)

        if investimentos_data  == "":
            investimentos_data = "08/02/2000"
        else:
            investimentos_data = investimentos_data  


        query_add_investimentos = """
                    INSERT INTO financas.investimentos(id_mes, descricao, investimento_tipo,data, valor)
                    VALUES (%s, %s, %s, %s, %s);
                    """

        novos_investimentos = []

        with st.form('form investimentos'):
            if st.form_submit_button('Adicionar Investimento'):
                novo_investimento = [investimentos_mes_ref, investimentos_descrição,investimentos_tipo, investimentos_data, investimentos_valor ]
                novos_investimentos.append(novo_investimento)
                adicionar_dados(query_add_investimentos,novo_investimento)
                st.write("Operação totalmente concluída.")    

            
            if novos_investimentos:
                novos_investimentos_df = pd.DataFrame(novos_investimentos, columns=investimentos.columns)
                worksheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1NyQsdyajS72NO4NoR6g52a2DVyXFTXOY6ATSu1H4iMY/edit?gid=0#gid=0').get_worksheet(0)
                
                # Obter o número de linhas existentes na planilha
                num_rows = len(worksheet.get_all_values())
                
                # Inserir os dados nas linhas subsequentes
                values_to_insert = novos_investimentos_df.values.tolist()
                worksheet.insert_rows(values_to_insert, num_rows + 1) 

    with st.expander('Empréstimos'):
        st.title('Empréstimos')
        emprestimos_mes_ref = st.selectbox('Selecione o mês referência:', ['01_2024','02_2024','03_2024','04_2024','05_2024',
                                                                        '06_2024','07_2024','08_2024','09_2024','10_2024',
                                                                        '11_2024','12_2024'], key='class-mesref_emprestimos')
        
        emprestimos_descrição =  st.text_input('Insirir Descrição', key = "inserir-descricao-emprestimos")
        emprestimos_destinatario =  st.text_input('Insirir Destinatário', key = "inserir-destinatario-emprestimos")

        emprestimos_data = st.text_input('Insirir Data', key = "inserir-data-emprestimos")
        emprestimos_valor = st.text_input('Insirir Valor', key = "inserir-valor-emprestimos")

        if emprestimos_valor == "":
            emprestimos_valor = 1.0
        else:
            emprestimos_valor = emprestimos_valor

        emprestimos_valor = float(emprestimos_valor)

        if emprestimos_data  == "":
            emprestimos_data = "08/02/2000"
        else:
            emprestimos_data = emprestimos_data


        query_add_emprestimos = """
                    INSERT INTO financas.emprestimos(id_mes, descricao, emprestimo_destinatario, data, valor)
                    VALUES (%s, %s, %s, %s, %s);
                    """

        novos_emprestimos = []

        with st.form('form emprestimos'):
            if st.form_submit_button('Adicionar Emprestimo'):
                novo_emprestimo= [emprestimos_mes_ref, emprestimos_descrição,emprestimos_destinatario, emprestimos_data, emprestimos_valor]
                novos_emprestimos.append(novo_emprestimo)
                adicionar_dados(query_add_emprestimos,novo_emprestimo)
                st.write("Operação totalmente concluída.")    

            
            if novos_emprestimos:
                novos_emprestimos_df = pd.DataFrame(novos_emprestimos, columns=emprestimos.columns)
                worksheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1MVMyWjNoiYZAJKLoYtEAwh-A4I_QHEErXsqkol9anoI/edit?gid=0#gid=0').get_worksheet(0)
                
                # Obter o número de linhas existentes na planilha
                num_rows = len(worksheet.get_all_values())
                
                # Inserir os dados nas linhas subsequentes
                values_to_insert = novos_emprestimos_df.values.tolist()
                worksheet.insert_rows(values_to_insert, num_rows + 1) 
        

    with st.expander('VR'):
            st.title('VR')

            #adicionando dados relativos a aba de débito: incluem a data, a classificação, o valor, a descrição

            #a partir do calculo de data conseguimos ter o mes e jogamos lá
            vr_mes_ref = st.selectbox('Selecione o mês referência:', ['1 - janeiro', '2 - fevereiro', '3 - março', '4 - abril', '5 - maio','6 - junho', '7 - julho','8 - agosto','9 - setembro','10 - outubro','11 - novembro','12 - dezembro'], key='class-mesref_vr')
            vr_data = st.text_input('Insirir Data',key = 'insirir-data-vr')
            vr_descrição =  st.text_input('Insirir Descrição', key = 'insirir-descricao-vr')
            vr_local =  st.text_input('Insirir Local', key = 'insirir-local-vr')
            vr_classificacao = st.selectbox('Selecione o tipo:', ['Almoço no escritório','Saídas','Saídas - Pitica','Rua','Casa','Outros'], key='class-vr')
            vr_valor = st.text_input('Insirir Valor', key = 'insirir-valor-vr')

            if vr_valor == "":
                vr_valor = 1.0
            else:
                vr_valor = vr_valor

            vr_valor = float(vr_valor)

            if vr_data  == "":
                vr_data = "08/02/2000"
            else:
                vr_data = vr_data    


            novos_vrs = []

            with st.form('form vr'):
                if st.form_submit_button('Adicionar Gastor VR'):
                    novo_vr = [ vr_data, vr_mes_ref, vr_descrição,vr_local,  vr_classificacao, vr_valor]
                    novos_vrs.append(novo_vr)

            if novos_vrs:
                novos_vrs_df = pd.DataFrame(novos_vrs, columns=vr.columns)
                worksheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1ZCMCzyrMdzIDkGnNZAErAyowwi8FzkivIFWhwEDyII8/edit#gid=0').get_worksheet(0)
                
                # Obter o número de linhas existentes na planilha
                num_rows = len(worksheet.get_all_values())
                
                # Inserir os dados nas linhas subsequentes
                values_to_insert = novos_vrs_df.values.tolist()
                worksheet.insert_rows(values_to_insert, num_rows + 1) 
                vr

with tab2:

    # pegando base de orcamento do excel e pegando o real gasto, além disso é feito alguns tratamentos
    orcamento_mensal_gastos = consultar_db("select * from financas.orcamento_mes")
    orcamento_mensal['id_class'] = orcamento_mensal['id_mes'] + orcamento_mensal['classificacao_orcamento']
    orcamento_mensal_gastos['id_class'] = orcamento_mensal_gastos['id_mes'] + orcamento_mensal_gastos['classificacao']
    orcamento_unificado = pd.merge(orcamento_mensal, orcamento_mensal_gastos, on='id_class', how='outer')
    orcamento_unificado['valor'] = orcamento_unificado['valor'].astype(float) 
    orcamento_unificado['Saldo'] = np.where(
    orcamento_unificado['classificacao'].isin(['Renda', 'Juntar']),
    orcamento_unificado['valor'] - orcamento_unificado['valor_orcamento'].astype(float),
    orcamento_unificado['valor_orcamento'].astype(float) - orcamento_unificado['valor'])
    orcamento_unificado['Saldo'] = round(orcamento_unificado['Saldo'],2) 

    with st.expander('Status Débito'):
        #criacao dos mestricos
        debito_orcamento =  orcamento_unificado[orcamento_unificado['classificacao'] == 'Débito']
        col1, col2, col3 =  st.columns(3)
        with col1:
            debito_saldo_atual  = debito_orcamento['Saldo'].iloc[-1]
            st.metric(label="Saldo atual", value=f"{round(debito_saldo_atual,2)}") 
        with col2: 
            debito_saldo_ano = debito_orcamento['Saldo'].sum()
            st.metric(label="Saldo anual", value=f"{round(debito_saldo_ano,2)}") 
        with col3:
            debito_media_mensal = debito_orcamento['valor'].mean()
            st.metric(label="Média mensal", value=f"{round(debito_media_mensal,2)}") 


        #primeiro gráfico que traz uma visão geral de gastos
        tipo_grafico = st.radio("Escolha a visualização", ['Saldo','valor'])

        
        graf_debito_mes = px.bar(
            debito_orcamento,
            x= 'id_mes_y',
            y =tipo_grafico,
            text = tipo_grafico,
            template =template_dash,
            color_discrete_sequence = ["#c1e0e0"]
        )
        graf_debito_mes.update_layout(
            showlegend=False,
            xaxis_title='Mês',
            yaxis_title='Saldo',
            plot_bgcolor =bg_color_dash,
            title={
                'text': f"<b> # GASTO MENSAL DÉBITO {tipo_grafico} <b>",
                'y': 0.9,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'}
        )

        graf_debito_mes.update_yaxes(visible=False,showticklabels=False)
        st.plotly_chart(graf_debito_mes, use_container_width=True)

        #criação do segundo gráfico
        #consultando no bd a base
        debito_agrupado_class =  consultar_db("SELECT id_mes, classificacao, SUM(valor) AS valor FROM financas.debito GROUP BY id_mes, classificacao ORDER BY id_mes, classificacao")
        
        cores = ["#fce7d2","#ffefa9","#f58f9a","#c0a1ae", "#bfd4ad","#000018","#578bc6"]

        #transformando o valor em float ao invés de decimal
              
        debito_agrupado_class['valor'] = debito_agrupado_class['valor'].astype(float)
        
        #criando id_mes "total"
        total_debito = debito_agrupado_class.groupby('classificacao')['valor'].sum().reset_index()
        total_debito['id_mes'] = 'Total'
        total_debito['Percentual'] = (total_debito['valor'] / total_debito['valor'].sum()) * 100
        debito_agrupado_class = pd.concat([debito_agrupado_class, total_debito], ignore_index=True)
        
        #criando coluna de gastos percentuais
        debito_agrupado_class['Percentual'] = (debito_agrupado_class['valor'] / debito_agrupado_class.groupby('id_mes')['valor'].transform('sum')) * 100
        debito_agrupado_class['Percentual'] = debito_agrupado_class['Percentual'].round(2)
        
        #radio para filtrar tipo de visualização

        radio_graf_debito_class = st.radio("Escolha a visualização", ['Percentual','valor',])

        #se o radio for igual a valor o "total" não aparece porque desconsidguraa
        #além disso se o valor for clicado aparece um metric com o gasto médio e filtro de classificação caso seja do interesse ter uma visão de gasto por classificação
        if radio_graf_debito_class == 'valor':
            debito_agrupado_class = debito_agrupado_class[debito_agrupado_class['id_mes'] != 'Total']
            meses_totais = consultar_db("SELECT COUNT(DISTINCT id_mes) AS total_id_mes FROM financas.debito")
            meses_totais = meses_totais['total_id_mes'].iloc[0]

            debito_agrupado_class_unico = debito_agrupado_class['classificacao'].unique()
            selected_classes = st.multiselect('Filtre as classificações:',debito_agrupado_class_unico, list(debito_agrupado_class_unico))
            debito_agrupado_class = debito_agrupado_class[debito_agrupado_class['classificacao'].isin(selected_classes)]
            debito_agrupado_class_media = round(debito_agrupado_class['valor'].sum()/meses_totais,2)
            
            st.metric(label="Média mensal", value=f"{round(debito_agrupado_class_media,2)}") 
            
        else:
            #se o radio for percentual apenas mostra o gráfico
            debito_agrupado_class = debito_agrupado_class
        
        #ajustando a ordem
        ordem_classificacao = ['Necessidade', 'Aplicativo de Transporte', 'Comida', 'Lazer - Comida','Lazer - Corinthians','Lazer - Outros','Outros']  # Exemplo de ordem que você pode ajustar
        debito_agrupado_class['classificacao'] = pd.Categorical(debito_agrupado_class['classificacao'], categories=ordem_classificacao, ordered=True)
        debito_agrupado_class = debito_agrupado_class.sort_values(by=['id_mes', 'classificacao'])
        
        graf_debito_class = px.bar(
            debito_agrupado_class,
            x= 'id_mes',
            y =radio_graf_debito_class,
            text = radio_graf_debito_class,
            color='classificacao',
            template =template_dash,
            color_discrete_sequence = cores,
                category_orders={
                    'id_mes': debito_agrupado_class['id_mes'].unique(),
                    'classificacao': ordem_classificacao }
        )

        graf_debito_class.update_layout(
            xaxis_title='Mês',
            yaxis_title='valor',
            plot_bgcolor =bg_color_dash,
            title={
                'text': f"<b> # GASTO DÉBITO POR TIPO - {radio_graf_debito_class} <b>",
                'y': 0.9,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'},
        )

        graf_debito_class.update_yaxes(visible=False,showticklabels=False)
        st.plotly_chart(graf_debito_class, use_container_width=True)


        st.title('Base Débito')

        with st.popover('Filtros'):
            debito_bd = consultar_db("select * from financas.debito") 
            filtro_id_mes = st.multiselect('Selecione o mês',debito_bd['id_mes'].unique(),list(debito_bd['id_mes'].unique()))
            debito_filtrado = debito[debito_bd['id_mes'].isin(filtro_id_mes)]
            filtro_class = st.multiselect('Selecione a classificação',debito_filtrado['classificacao'].unique(),list(debito_filtrado['classificacao'].unique()))
            debito_filtrado = debito_filtrado[debito_filtrado['classificacao'].isin(filtro_class)]
        debito_filtrado

     
    