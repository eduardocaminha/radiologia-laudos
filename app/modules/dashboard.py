"""
Dashboard principal com estatísticas da base Bronze de laudos
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import execute_query

def renderizar_dashboard(conn):
    """
    Renderiza dashboard completo com estatísticas dos laudos extraídos
    """
    
    st.header("📊 Dashboard - Laudos Radiológicos")
    st.markdown("Análise completa dos laudos extraídos da base Bronze")
    
    # =====================================================================
    # FILTROS GLOBAIS
    # =====================================================================
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filtros")
    
    # Filtro de período
    periodo_opcoes = {
        "Últimos 7 dias": 7,
        "Últimos 30 dias": 30,
        "Últimos 90 dias": 90,
        "Último ano": 365,
        "Tudo": None
    }
    
    periodo_selecionado = st.sidebar.selectbox(
        "Período de análise:",
        list(periodo_opcoes.keys()),
        index=1  # Default: 30 dias
    )
    
    dias_filtro = periodo_opcoes[periodo_selecionado]
    
    # Filtro de fonte
    fonte_selecionada = st.sidebar.multiselect(
        "Fonte dos laudos:",
        ["HSP", "PSC"],
        default=["HSP", "PSC"]
    )
    
    if not fonte_selecionada:
        st.warning("⚠️ Selecione pelo menos uma fonte")
        return
    
    # Carregar modalidades disponíveis
    query_modalidades_disponiveis = """
    SELECT DISTINCT nome_modalidade 
    FROM innovation_dev.gold.radiologia_laudos_modalidades
    WHERE ativo = TRUE
    ORDER BY nome_modalidade
    """
    df_modalidades_disponiveis = execute_query(conn, query_modalidades_disponiveis)
    modalidades_disponiveis = df_modalidades_disponiveis['nome_modalidade'].tolist() if len(df_modalidades_disponiveis) > 0 else []
    
    # Filtro de modalidades
    modalidades_selecionadas = st.sidebar.multiselect(
        "Modalidades:",
        modalidades_disponiveis,
        default=modalidades_disponiveis,
        help="Filtrar por tipo de exame (TC, RM, etc.)"
    )
    
    # Carregar descrições disponíveis
    query_descricoes_disponiveis = """
    SELECT DISTINCT descricao 
    FROM innovation_dev.gold.radiologia_laudos_descricoes
    WHERE ativo = TRUE
    ORDER BY descricao
    """
    df_descricoes_disponiveis = execute_query(conn, query_descricoes_disponiveis)
    descricoes_disponiveis = df_descricoes_disponiveis['descricao'].tolist() if len(df_descricoes_disponiveis) > 0 else []
    
    # Filtro de descrições
    descricoes_selecionadas = st.sidebar.multiselect(
        "Descrições:",
        descricoes_disponiveis,
        default=[],
        help="Filtrar por região anatômica ou técnica (ex: ABDOME SUPERIOR, CRANIO, etc.)"
    )
    
    # Construir WHERE clause base
    where_clauses = []
    
    if dias_filtro:
        where_clauses.append(f"tms_procedimento_realizado >= CURRENT_DATE - INTERVAL {dias_filtro} DAYS")
    
    # Construir IN clause para fontes
    fontes_quoted = [f"'{f}'" for f in fonte_selecionada]
    fontes_in = ','.join(fontes_quoted)
    where_clauses.append(f"fonte IN ({fontes_in})")
    
    where_sql = " AND ".join(where_clauses)
    
    # Construir filtros adicionais para modalidades e descrições
    filtros_adicionais = []
    
    if modalidades_selecionadas and len(modalidades_selecionadas) < len(modalidades_disponiveis):
        modalidades_quoted = [f"'{m}'" for m in modalidades_selecionadas]
        modalidades_in = ','.join(modalidades_quoted)
        filtros_adicionais.append(f"m.nome_modalidade IN ({modalidades_in})")
    
    if descricoes_selecionadas:
        descricoes_quoted = [f"'{d}'" for d in descricoes_selecionadas]
        descricoes_in = ','.join(descricoes_quoted)
        filtros_adicionais.append(f"d.descricao IN ({descricoes_in})")
    
    filtros_adicionais_sql = " AND " + " AND ".join(filtros_adicionais) if filtros_adicionais else ""
    
    # Construir query base com JOINs (se houver filtros de modalidade ou descrição)
    if filtros_adicionais_sql:
        # Precisa fazer JOIN com as tabelas Gold
        from_clause = """
        FROM innovation_dev.bronze.radiologia_laudos_extraidos l
        INNER JOIN innovation_dev.gold.radiologia_laudos_procedimentos p
            ON l.cd_procedimento = p.cd_procedimento
        INNER JOIN innovation_dev.gold.radiologia_laudos_modalidades m
            ON p.id_modalidade = m.id_modalidade
        LEFT JOIN innovation_dev.gold.radiologia_laudos_descricoes d
            ON d.id_descricao IN (p.id_descricao_1, p.id_descricao_2, p.id_descricao_3, 
                                  p.id_descricao_4, p.id_descricao_5, p.id_descricao_6, p.id_descricao_7)
        """
        where_clause_completo = f"WHERE {where_sql} AND p.ativo = TRUE AND m.ativo = TRUE{filtros_adicionais_sql}"
        alias_tabela = "l"
    else:
        # Sem filtros adicionais, query simples
        from_clause = "FROM innovation_dev.bronze.radiologia_laudos_extraidos l"
        where_clause_completo = f"WHERE {where_sql}"
        alias_tabela = "l"
    
    # =====================================================================
    # MÉTRICAS PRINCIPAIS (KPIs)
    # =====================================================================
    
    st.subheader("📈 Indicadores Principais")
    
    query_kpis = f"""
    SELECT 
        COUNT(DISTINCT {alias_tabela}.accession_number) as total_laudos,
        COUNT(DISTINCT {alias_tabela}.accession_number) as laudos_unicos,
        COUNT(DISTINCT {alias_tabela}.cd_paciente) as pacientes_unicos,
        COUNT(DISTINCT {alias_tabela}.cd_procedimento) as procedimentos_distintos,
        COUNT(DISTINCT DATE({alias_tabela}.tms_procedimento_realizado)) as dias_com_dados,
        MIN({alias_tabela}.tms_procedimento_realizado) as data_min,
        MAX({alias_tabela}.tms_procedimento_realizado) as data_max
    {from_clause}
    {where_clause_completo}
    """
    
    df_kpis = execute_query(conn, query_kpis)
    
    # Query para total geral (sem filtros de modalidade/descrição) para comparação
    query_total_geral = f"""
    SELECT COUNT(DISTINCT accession_number) as total_geral
    FROM innovation_dev.bronze.radiologia_laudos_extraidos
    WHERE {where_sql}
    """
    df_total_geral = execute_query(conn, query_total_geral)
    
    if len(df_kpis) > 0:
        kpi = df_kpis.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📋 Total de Laudos",
                f"{kpi['total_laudos']:,}",
                help="Total de registros de laudos"
            )
        
        with col2:
            st.metric(
                "👥 Pacientes Únicos",
                f"{kpi['pacientes_unicos']:,}",
                help="Quantidade de pacientes distintos"
            )
        
        with col3:
            st.metric(
                "🔬 Procedimentos",
                f"{kpi['procedimentos_distintos']:,}",
                help="Tipos de procedimentos realizados"
            )
        
        with col4:
            media_dia = kpi['total_laudos'] / max(kpi['dias_com_dados'], 1)
            st.metric(
                "📊 Média/Dia",
                f"{media_dia:,.0f}",
                help="Média de laudos por dia"
            )
        
        # Período dos dados
        st.caption(f"📅 Período: {kpi['data_min']} até {kpi['data_max']}")
        
        # Aviso sobre cobertura de mapeamento
        if len(df_total_geral) > 0:
            total_geral = df_total_geral.iloc[0]['total_geral']
            total_filtrado = kpi['total_laudos']
            
            if total_geral > total_filtrado:
                cobertura_pct = (total_filtrado / total_geral * 100) if total_geral > 0 else 0
                laudos_nao_mapeados = total_geral - total_filtrado
                
                if filtros_adicionais_sql:
                    st.warning(f"⚠️ **Filtros ativos**: Mostrando {total_filtrado:,} de {total_geral:,} laudos ({cobertura_pct:.1f}%). {laudos_nao_mapeados:,} laudos não atendem aos filtros ou não estão mapeados.")
                else:
                    st.warning(f"⚠️ **Cobertura de mapeamento**: {total_filtrado:,} de {total_geral:,} laudos estão mapeados ({cobertura_pct:.1f}%). {laudos_nao_mapeados:,} laudos ainda não têm procedimentos cadastrados nas tabelas Gold.")
    
    st.markdown("---")
    
    # =====================================================================
    # GRÁFICOS - LINHA 1: VOLUME E TENDÊNCIAS
    # =====================================================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Volume de Laudos por Dia")
        
        query_volume_dia = f"""
        SELECT 
            DATE({alias_tabela}.tms_procedimento_realizado) as data,
            COUNT(DISTINCT {alias_tabela}.accession_number) as total_laudos,
            COUNT(DISTINCT {alias_tabela}.cd_paciente) as pacientes
        {from_clause}
        {where_clause_completo}
        GROUP BY data
        ORDER BY data
        """
        
        df_volume = execute_query(conn, query_volume_dia)
        
        if len(df_volume) > 0:
            fig_volume = go.Figure()
            
            fig_volume.add_trace(go.Scatter(
                x=df_volume['data'],
                y=df_volume['total_laudos'],
                mode='lines+markers',
                name='Laudos',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            
            fig_volume.update_layout(
                height=350,
                xaxis_title="Data",
                yaxis_title="Quantidade de Laudos",
                hovermode='x unified',
                showlegend=False
            )
            
            st.plotly_chart(fig_volume, use_container_width=True)
        else:
            st.info("Sem dados para o período selecionado")
    
    with col2:
        st.subheader("🏥 Distribuição por Fonte")
        
        query_fonte = f"""
        SELECT 
            {alias_tabela}.fonte,
            COUNT(DISTINCT {alias_tabela}.accession_number) as total_laudos,
            COUNT(DISTINCT {alias_tabela}.cd_paciente) as pacientes,
            COUNT(DISTINCT {alias_tabela}.cd_procedimento) as procedimentos
        {from_clause}
        {where_clause_completo}
        GROUP BY {alias_tabela}.fonte
        ORDER BY total_laudos DESC
        """
        
        df_fonte = execute_query(conn, query_fonte)
        
        if len(df_fonte) > 0:
            fig_fonte = px.pie(
                df_fonte,
                values='total_laudos',
                names='fonte',
                title='',
                color_discrete_sequence=['#1f77b4', '#ff7f0e']
            )
            
            fig_fonte.update_traces(
                textposition='inside',
                textinfo='percent+label+value',
                hovertemplate='<b>%{label}</b><br>Laudos: %{value:,}<br>Percentual: %{percent}<extra></extra>'
            )
            
            fig_fonte.update_layout(height=350)
            
            st.plotly_chart(fig_fonte, use_container_width=True)
        else:
            st.info("Sem dados para o período selecionado")
    
    st.markdown("---")
    
    # =====================================================================
    # GRÁFICOS - LINHA 2: MODALIDADES E PROCEDIMENTOS
    # =====================================================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔬 Top 10 Modalidades")
        
        # Query sempre precisa de JOIN com modalidades
        query_modalidades = f"""
        SELECT 
            m.nome_modalidade,
            COUNT(DISTINCT l.accession_number) as total_laudos,
            COUNT(DISTINCT l.cd_paciente) as pacientes_unicos
        FROM innovation_dev.bronze.radiologia_laudos_extraidos l
        INNER JOIN innovation_dev.gold.radiologia_laudos_procedimentos p
            ON l.cd_procedimento = p.cd_procedimento
        INNER JOIN innovation_dev.gold.radiologia_laudos_modalidades m
            ON p.id_modalidade = m.id_modalidade
        {('LEFT JOIN innovation_dev.gold.radiologia_laudos_descricoes d ON d.id_descricao IN (p.id_descricao_1, p.id_descricao_2, p.id_descricao_3, p.id_descricao_4, p.id_descricao_5, p.id_descricao_6, p.id_descricao_7)') if descricoes_selecionadas else ''}
        WHERE {where_sql}
          AND p.ativo = TRUE
          AND m.ativo = TRUE
          {filtros_adicionais_sql}
        GROUP BY m.nome_modalidade
        ORDER BY total_laudos DESC
        LIMIT 10
        """
        
        df_modalidades = execute_query(conn, query_modalidades)
        
        if len(df_modalidades) > 0:
            fig_modalidades = px.bar(
                df_modalidades,
                x='total_laudos',
                y='nome_modalidade',
                orientation='h',
                title='',
                color='total_laudos',
                color_continuous_scale='Blues'
            )
            
            fig_modalidades.update_layout(
                height=400,
                xaxis_title="Quantidade de Laudos",
                yaxis_title="",
                showlegend=False,
                yaxis={'categoryorder':'total ascending'}
            )
            
            fig_modalidades.update_traces(
                hovertemplate='<b>%{y}</b><br>Laudos: %{x:,}<extra></extra>'
            )
            
            st.plotly_chart(fig_modalidades, use_container_width=True)
        else:
            st.info("Sem dados de modalidades mapeadas")
    
    with col2:
        st.subheader("📊 Top 10 Procedimentos")
        
        # Query sempre precisa de JOIN com procedimentos
        query_procedimentos = f"""
        SELECT 
            p.cd_procedimento,
            p.nm_procedimento,
            COUNT(DISTINCT l.accession_number) as total_laudos,
            COUNT(DISTINCT l.cd_paciente) as pacientes_unicos
        FROM innovation_dev.bronze.radiologia_laudos_extraidos l
        INNER JOIN innovation_dev.gold.radiologia_laudos_procedimentos p
            ON l.cd_procedimento = p.cd_procedimento
        INNER JOIN innovation_dev.gold.radiologia_laudos_modalidades m
            ON p.id_modalidade = m.id_modalidade
        {('LEFT JOIN innovation_dev.gold.radiologia_laudos_descricoes d ON d.id_descricao IN (p.id_descricao_1, p.id_descricao_2, p.id_descricao_3, p.id_descricao_4, p.id_descricao_5, p.id_descricao_6, p.id_descricao_7)') if descricoes_selecionadas else ''}
        WHERE {where_sql}
          AND p.ativo = TRUE
          AND m.ativo = TRUE
          {filtros_adicionais_sql}
        GROUP BY p.cd_procedimento, p.nm_procedimento
        ORDER BY total_laudos DESC
        LIMIT 10
        """
        
        df_procedimentos = execute_query(conn, query_procedimentos)
        
        if len(df_procedimentos) > 0:
            # Truncar nomes longos
            df_procedimentos['nome_curto'] = df_procedimentos['nm_procedimento'].str[:50] + '...'
            
            fig_procedimentos = px.bar(
                df_procedimentos,
                x='total_laudos',
                y='nome_curto',
                orientation='h',
                title='',
                color='total_laudos',
                color_continuous_scale='Oranges'
            )
            
            fig_procedimentos.update_layout(
                height=400,
                xaxis_title="Quantidade de Laudos",
                yaxis_title="",
                showlegend=False,
                yaxis={'categoryorder':'total ascending'}
            )
            
            fig_procedimentos.update_traces(
                hovertemplate='<b>%{customdata[0]}</b><br>Código: %{customdata[1]}<br>Laudos: %{x:,}<extra></extra>',
                customdata=df_procedimentos[['nm_procedimento', 'cd_procedimento']].values
            )
            
            st.plotly_chart(fig_procedimentos, use_container_width=True)
        else:
            st.info("Sem dados de procedimentos mapeados")
    
    st.markdown("---")
    
    # =====================================================================
    # GRÁFICOS - LINHA 3: ANÁLISE TEMPORAL
    # =====================================================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 Volume por Dia da Semana")
        
        query_dia_semana = f"""
        SELECT 
            DAYOFWEEK({alias_tabela}.tms_procedimento_realizado) as dia_num,
            CASE DAYOFWEEK({alias_tabela}.tms_procedimento_realizado)
                WHEN 1 THEN 'Domingo'
                WHEN 2 THEN 'Segunda'
                WHEN 3 THEN 'Terça'
                WHEN 4 THEN 'Quarta'
                WHEN 5 THEN 'Quinta'
                WHEN 6 THEN 'Sexta'
                WHEN 7 THEN 'Sábado'
            END as dia_semana,
            COUNT(DISTINCT {alias_tabela}.accession_number) as total_laudos,
            AVG(COUNT(DISTINCT {alias_tabela}.accession_number)) OVER () as media
        {from_clause}
        {where_clause_completo}
        GROUP BY dia_num
        ORDER BY dia_num
        """
        
        df_dia_semana = execute_query(conn, query_dia_semana)
        
        if len(df_dia_semana) > 0:
            fig_dia_semana = go.Figure()
            
            fig_dia_semana.add_trace(go.Bar(
                x=df_dia_semana['dia_semana'],
                y=df_dia_semana['total_laudos'],
                marker_color='#2ca02c',
                name='Laudos'
            ))
            
            # Linha de média
            fig_dia_semana.add_trace(go.Scatter(
                x=df_dia_semana['dia_semana'],
                y=df_dia_semana['media'],
                mode='lines',
                line=dict(color='red', dash='dash', width=2),
                name='Média'
            ))
            
            fig_dia_semana.update_layout(
                height=350,
                xaxis_title="Dia da Semana",
                yaxis_title="Quantidade de Laudos",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_dia_semana, use_container_width=True)
        else:
            st.info("Sem dados para análise semanal")
    
    with col2:
        st.subheader("🕐 Volume por Hora do Dia")
        
        query_hora = f"""
        SELECT 
            HOUR({alias_tabela}.tms_procedimento_realizado) as hora,
            COUNT(DISTINCT {alias_tabela}.accession_number) as total_laudos
        {from_clause}
        {where_clause_completo}
        GROUP BY hora
        ORDER BY hora
        """
        
        df_hora = execute_query(conn, query_hora)
        
        if len(df_hora) > 0:
            fig_hora = px.line(
                df_hora,
                x='hora',
                y='total_laudos',
                markers=True,
                title=''
            )
            
            fig_hora.update_traces(
                line_color='#9467bd',
                marker=dict(size=8)
            )
            
            fig_hora.update_layout(
                height=350,
                xaxis_title="Hora do Dia",
                yaxis_title="Quantidade de Laudos",
                xaxis=dict(tickmode='linear', tick0=0, dtick=2)
            )
            
            st.plotly_chart(fig_hora, use_container_width=True)
        else:
            st.info("Sem dados para análise horária")
    
    st.markdown("---")
    
    # =====================================================================
    # TABELAS DETALHADAS
    # =====================================================================
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Detalhamento por Modalidade")
        
        # Query sempre precisa de JOIN com modalidades
        query_detalhamento = f"""
        SELECT 
            m.nome_modalidade as Modalidade,
            COUNT(DISTINCT l.accession_number) as `Total Laudos`,
            COUNT(DISTINCT l.cd_paciente) as `Pacientes Únicos`,
            COUNT(DISTINCT l.cd_procedimento) as `Procedimentos Distintos`,
            ROUND(COUNT(DISTINCT l.accession_number) * 100.0 / SUM(COUNT(DISTINCT l.accession_number)) OVER (), 2) as `% do Total`
        FROM innovation_dev.bronze.radiologia_laudos_extraidos l
        INNER JOIN innovation_dev.gold.radiologia_laudos_procedimentos p
            ON l.cd_procedimento = p.cd_procedimento
        INNER JOIN innovation_dev.gold.radiologia_laudos_modalidades m
            ON p.id_modalidade = m.id_modalidade
        {('LEFT JOIN innovation_dev.gold.radiologia_laudos_descricoes d ON d.id_descricao IN (p.id_descricao_1, p.id_descricao_2, p.id_descricao_3, p.id_descricao_4, p.id_descricao_5, p.id_descricao_6, p.id_descricao_7)') if descricoes_selecionadas else ''}
        WHERE {where_sql}
          AND p.ativo = TRUE
          AND m.ativo = TRUE
          {filtros_adicionais_sql}
        GROUP BY m.nome_modalidade
        ORDER BY `Total Laudos` DESC
        """
        
        df_detalhamento = execute_query(conn, query_detalhamento)
        
        if len(df_detalhamento) > 0:
            st.dataframe(
                df_detalhamento,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem dados de modalidades mapeadas")
    
    with col2:
        st.subheader("🏷️ Detalhamento por Descrição")
        
        # Query para agrupar por descrição (região anatômica/técnica)
        query_descricoes = f"""
        SELECT 
            d.descricao as `Descrição`,
            COUNT(DISTINCT l.accession_number) as `Total Laudos`,
            COUNT(DISTINCT l.cd_paciente) as `Pacientes Únicos`,
            COUNT(DISTINCT l.cd_procedimento) as `Procedimentos Distintos`,
            ROUND(COUNT(DISTINCT l.accession_number) * 100.0 / SUM(COUNT(DISTINCT l.accession_number)) OVER (), 2) as `% do Total`
        FROM innovation_dev.bronze.radiologia_laudos_extraidos l
        INNER JOIN innovation_dev.gold.radiologia_laudos_procedimentos p
            ON l.cd_procedimento = p.cd_procedimento
        INNER JOIN innovation_dev.gold.radiologia_laudos_modalidades m
            ON p.id_modalidade = m.id_modalidade
        INNER JOIN innovation_dev.gold.radiologia_laudos_descricoes d
            ON d.id_descricao IN (p.id_descricao_1, p.id_descricao_2, p.id_descricao_3, 
                                  p.id_descricao_4, p.id_descricao_5, p.id_descricao_6, p.id_descricao_7)
        WHERE {where_sql}
          AND p.ativo = TRUE
          AND m.ativo = TRUE
          AND d.ativo = TRUE
          {' AND ' + ' AND '.join(filtros_adicionais) if filtros_adicionais else ''}
        GROUP BY d.descricao
        ORDER BY `Total Laudos` DESC
        LIMIT 20
        """
        
        df_descricoes = execute_query(conn, query_descricoes)
        
        if len(df_descricoes) > 0:
            st.dataframe(
                df_descricoes,
                use_container_width=True,
                hide_index=True
            )
            st.caption("💡 Use o filtro 'Descrições' no sidebar para focar em regiões específicas")
        else:
            st.info("Sem dados de descrições mapeadas")
    
    st.markdown("---")
    
    # =====================================================================
    # MÉTRICAS DE QUALIDADE E EXECUÇÃO
    # =====================================================================
    
    st.subheader("⚙️ Métricas de Execução dos Jobs")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Últimas Execuções**")
        
        query_execucoes = f"""
        SELECT 
            dt_processamento as `Data Processamento`,
            modo_execucao as `Modo`,
            laudos_extraidos as `Laudos`,
            procedimentos_ativos as `Procedimentos`,
            DATE_FORMAT(tms_execucao, 'dd/MM/yyyy HH:mm') as `Executado em`
        FROM innovation_dev.bronze.radiologia_laudos_metricas_job
        ORDER BY tms_execucao DESC
        LIMIT 10
        """
        
        df_execucoes = execute_query(conn, query_execucoes)
        
        if len(df_execucoes) > 0:
            st.dataframe(
                df_execucoes,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem dados de execuções")
    
    with col2:
        st.markdown("**📈 Estatísticas de Carga**")
        
        query_stats_carga = f"""
        SELECT 
            modo_execucao as `Modo de Execução`,
            COUNT(*) as `Total Execuções`,
            SUM(laudos_extraidos) as `Total Laudos`,
            AVG(laudos_extraidos) as `Média Laudos/Exec`,
            MAX(laudos_extraidos) as `Máximo`
        FROM innovation_dev.bronze.radiologia_laudos_metricas_job
        GROUP BY modo_execucao
        ORDER BY `Total Execuções` DESC
        """
        
        df_stats = execute_query(conn, query_stats_carga)
        
        if len(df_stats) > 0:
            # Formatar números
            df_stats['Média Laudos/Exec'] = df_stats['Média Laudos/Exec'].round(0)
            
            st.dataframe(
                df_stats,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem estatísticas de carga")
    
    # Footer
    st.markdown("---")
    st.caption(f"🔄 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
