import streamlit as st
import pandas as pd
import numpy as np
import duckdb
from io import BytesIO
from streamlit_ace import st_ace
from annotated_text import annotated_text
from streamlit_option_menu import option_menu
from datetime import datetime

hide_st_style = """
                    <style>
                    button.MuiButton-containedPrimary {background-color: green !important}
                    .MuiGrid-justify-content-xs-flex-end {background-color: green !important}
                    .MuiButtonBase-root {background-color: green !important}
                    .MuiButton-contained {background-color: green !important}
                    .MuiButton-containedPrimary {background-color: green}
                    </style>
                    """
st.markdown(hide_st_style, unsafe_allow_html=True)

with st.sidebar:
    selected = option_menu(
        menu_title="",
        options=['Welcome', 'Get Started'],
        icons=['house','gear']
    )

# Function to load the uploaded files
def load_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            data = pd.read_csv(uploaded_file)
            return {'Sheet1': data}
        elif uploaded_file.name.endswith('.xlsx'):
            xls = pd.ExcelFile(uploaded_file, engine='openpyxl')
            sheets = {sheet_name: pd.read_excel(xls, sheet_name) for sheet_name in xls.sheet_names}
            return sheets
        else:
            st.error(f"Unsupported file type: {uploaded_file.name}")
            return None
    except ValueError as ve:
        st.error(f"ValueError: {ve}")
        return None
    except Exception as e:
        st.error(f"An error occurred while reading the file: {e}")
        return None

# Function to query data using duckdb
def query_data(con, query):
    try:
        result = con.execute(query).fetchdf()
        return result
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

# Function to convert dataframe to CSV bytes
def convert_df_to_csv_bytes(df):
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

if selected == 'Welcome':
    st.image('Header3.png')
    annotated_text("Want to do ", ("analysis of your CSVs", "", "#83f28f"), " without learning Excel/Pandas formulas or using Excel's UI?")
    st.image('main2.png')
    annotated_text("This app will turn your browser into ", ("in-memory offline data warehouse", "", "#83f28f"),
                   " so you can write SQL queries on top of CSV/Excels without the hassle of moving the files to cloud data warehouse, thus saving ⏰ & 💰")
    st.subheader("Features")
    st.write("1️⃣ **Quick Adhoc analysis using SQL** - No need to learn Excel Formulas or Pandas formulas for analysis")
    st.write("2️⃣ **Quick Advance Analysis** - Upload multiple files at once, query them together in single query")
    st.write("3️⃣ **Works offline** - We are not storing your data (neither are we using AI!!)")
    st.write("4️⃣ **Blazing Fast** - Just one click to upload the files, that's it")
    st.markdown('---')
    st.markdown('Made with :heart: by [Sahil Choudhary](https://www.linkedin.com/in/offiicialhksahil/)')

if selected == 'Get Started':
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Data Preview"
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []

    st.image("Header3.png")
    st.write("Upload your CSV(s) from the left menu & start writing SQL on top of it")

    st.sidebar.title("Upload Files")
    uploaded_files = st.sidebar.file_uploader("Upload CSV or Excel files", type=['csv', 'xlsx'], accept_multiple_files=True)

    if uploaded_files:
        file_names = [uploaded_file.name for uploaded_file in uploaded_files]
        selected_file = st.sidebar.radio("Select a file", file_names)

        con = duckdb.connect(database=':memory:')

        for i, uploaded_file in enumerate(uploaded_files):
            tables = load_data(uploaded_file)
            if tables is not None:
                for sheet_name, data in tables.items():
                    table_name = f"table{i + 1}_{sheet_name}"
                    con.register(table_name, data)

            if uploaded_file.name == selected_file:
                selected_data = tables
                selected_table_name = [f"table{i + 1}_{sheet_name}" for sheet_name in tables.keys()]

        if selected_data is not None:
            st.code(f"Tip: You can use the following table names in your SQL queries: {', '.join(selected_table_name)}")

            query = st_ace(
                placeholder=f"Enter your SQL Queries here (example, SELECT * FROM {selected_table_name[0]} )",
                language="sql",
                theme="eclipse",
                key=f"query_{selected_table_name[0]}",
                font_size=18
            )

            query_result = None

            if query:
                query_result = query_data(con, query)
                st.session_state.active_tab = "Query Results"
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Check if the last query is the same as the new query
                if not st.session_state.query_history or st.session_state.query_history[-1][1] != query:
                    st.session_state.query_history.append((timestamp, query))

            tabs = ["Data Preview", "Metadata", "Query Results", "Query History"]
            active_tab = st.radio("Select a tab", tabs, index=tabs.index(st.session_state.active_tab), horizontal=True)

            if active_tab == "Data Preview":
                for sheet_name, data in selected_data.items():
                    st.subheader(f"Sheet: {sheet_name}")
                    st.write(data)

            elif active_tab == "Metadata":
                for sheet_name, data in selected_data.items():
                    st.subheader(f"Metadata for Sheet: {sheet_name}")
                    # Display number of rows and columns
                    num_rows, num_columns = data.shape
                    st.info(f"Number of columns: {num_columns} & Number of rows: {num_rows}")

                    # Process numeric columns
                    if not data.select_dtypes(include=[np.number]).empty:
                        stats = data.describe(include=[np.number])
                        stats = stats.loc[stats.index.intersection(['count', 'mean', 'min', 'max'])]

                    # Process string columns
                    string_columns = data.select_dtypes(include=['object']).columns
                    additional_info_list = []
                    for col in string_columns:
                        missing_percentage = data[col].isna().mean() * 100
                        distinct_percentage = data[col].nunique() / len(data) * 100
                        avg_length = data[col].dropna().apply(len).mean()
                        most_frequent = data[col].mode().iloc[0] if not data[col].mode().empty else None
                        additional_info_list.append({
                            'Column Name': col,
                            '% Missing Values': missing_percentage,
                            '% Distinct Values': distinct_percentage,
                            'Average Length': avg_length,
                            'Most Frequent Value': most_frequent
                        })
                    additional_info = pd.DataFrame(additional_info_list)

                    # Query for DuckDB data types
                    duckdb_dtypes_query = f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{sheet_name}'
                    """
                    duckdb_dtypes = con.execute(duckdb_dtypes_query).fetchdf()
                    duckdb_dtypes = duckdb_dtypes.set_index('column_name')

                    if not data.select_dtypes(include=[np.number]).empty:
                        merged_info = pd.concat([stats.T, additional_info.set_index('Column Name')], axis=1)
                    else:
                        merged_info = additional_info.set_index('Column Name')

                    merged_info = merged_info.reindex(columns=['count', 'mean', 'min', 'max', '% Missing Values', '% Distinct Values', 'Average Length', 'Most Frequent Value'])
                    merged_info = pd.concat([merged_info, duckdb_dtypes], axis=1)
                    merged_info = merged_info.rename(columns={'data_type': 'DuckDB Data Type'})
                    merged_info = merged_info[['DuckDB Data Type'] + [col for col in merged_info.columns if col != 'DuckDB Data Type']]

                    st.write(merged_info)

            elif active_tab == "Query Results":
                if query_result is not None:
                    num_rows = len(query_result)
                    st.info(f"Number of rows returned: {num_rows}")

                    st.write(query_result)

                    csv_bytes = convert_df_to_csv_bytes(query_result)
                    st.download_button(
                        label="Download Query Results as CSV",
                        data=csv_bytes,
                        file_name=f"{selected_table_name[0]}_query_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Run your query first to populate this section")

            elif active_tab == "Query History":
                if st.session_state.query_history:
                    for i, (timestamp, q) in enumerate(reversed(st.session_state.query_history), 1):
                        st.markdown(f'<div style="display: flex; justify-content: space-between;">'
                                    f'<div style="flex-shrink: 0; color:gray; margin-left: 10px;"> Query ran at {timestamp}</div>'
                                    f'</div>', unsafe_allow_html=True)
                        st.code(q)
                else:
                    st.info("Run your query first to populate this section")

        con.close()
