"""Template de prompt principal para estruturação de laudos radiológicos.

Este módulo fornece o template de prompt usado para guiar o LangExtract
na categorização de textos de laudos radiológicos em seções semânticas
(prefixo, corpo, sufixo), com anotações adequadas de significância clínica.

O prompt inclui instruções detalhadas com diretrizes para lidar com diferentes
formatos de laudo e casos de borda, garantindo uma estruturação consistente e
precisa em diversos tipos de exames de radiologia.
"""

import textwrap

PROMPT_INSTRUCTION = textwrap.dedent(
    """\
    # RadExtract Prompt

    ## Descrição da Tarefa

    Você é um assistente médico especializado em categorizar texto de laudos
    radiológicos em seções:

    - **findings_prefix** -- Todo o texto que aparece antes do conteúdo de
      "achados" propriamente dito.
    - **findings_body** -- A seção principal de *achados* (Findings). Cada
      achado é classificado em uma seção possível por meio de uma lista de
      atributos, alguns dos quais também podem ser atribuídos a um
      subcabeçalho.
    - **findings_suffix** -- Qualquer texto que apareça depois da parte de
      achados (como "Impressão", "Conclusão" ou outro conteúdo conclusivo).

    ### Categorias de Seção:
    - **findings_prefix**: Use apenas para informações de cabeçalho que vêm
      antes dos achados clínicos (detalhes do exame, indicação clínica,
      técnica). Nunca use para observações clínicas ou achados patológicos.
    - **findings_body**: Use para todos os achados clínicos, observações e
      descrições patológicas.
    - **findings_suffix**: Use apenas para conclusões, impressões ou
      recomendações que aparecem depois dos achados principais.

    ### Regra Crítica:
    Se um laudo contiver apenas achados clínicos, sem nenhuma informação de
    cabeçalho, **não** crie uma extração findings_prefix. Comece diretamente
    com extrações findings_body para o conteúdo clínico.

    **Exemplo de conteúdo apenas com achados (SEM prefixo necessário):**
    Entrada: "Há pequeno derrame articular. A cartilagem apresenta
    afinamento."
    Correto: Criar apenas extrações findings_body para cada achado clínico.
    Incorreto: Não categorizar achados clínicos como findings_prefix.

    ### Padrões Profissionais de Saída:
    Todo o texto extraído deve manter a correção gramatical e a coerência
    profissional esperadas em laudos radiológicos. Garanta que:
    - Todas as frases estejam completas e gramaticalmente corretas
    - A terminologia médica seja usada de forma apropriada e consistente
    - A linguagem permaneça profissional e com tom clínico
    - Erros óbvios de digitação sejam corrigidos
    - Qualquer modificação preserve o significado médico pretendido
    - Pequenos erros de grafia e pontuação sejam corrigidos

    ### Seções de prefixo ou sufixo vazias:
    Crie extrações apenas para seções que realmente existam no texto. Não
    crie seções findings_prefix ou findings_suffix vazias se não houver
    conteúdo correspondente no texto de origem. Se o texto trouxer apenas
    achados, sem impressão/conclusão, não crie extração findings_suffix.

    ### Diretrizes de Uso das Seções:

    **findings_prefix**: Reservada exclusivamente para informações de cabeçalho
    que aparecem antes dos achados clínicos, como:
    - Detalhes do exame (tipo de estudo, técnica)
    - Indicação clínica ou história
    - Estudos de comparação mencionados
    - Parâmetros técnicos

    **findings_body**: Contém os achados clínicos e observações do estudo de
    imagem.

    **findings_suffix**: Reservada para o conteúdo conclusivo que segue os
    achados, como impressões ou recomendações.

    **Regra crítica**: Achados clínicos nunca devem ser categorizados como
    conteúdo de prefixo. Se um laudo começar diretamente com observações
    clínicas, sem cabeçalho, crie apenas extrações findings_body e
    findings_suffix, conforme apropriado.

    ### Orientação especial para a organização de findings_prefix:
    Quando o laudo tiver informações de prefixo bem detalhadas, com seções
    claramente identificadas (como EXAMINATION, CLINICAL INDICATION,
    COMPARISON, TECHNIQUE), crie extrações separadas para cada seção ao invés
    de um único bloco grande. Use o atributo "section" para rotular cada
    parte:
    - "Examination" para o tipo/título do exame
    - "Clinical Indication" para a história/indicação clínica
    - "Comparison" para exames prévios mencionados
    - "Technique" para parâmetros e detalhes técnicos de aquisição

    **Importante:** Mesmo quando as informações de exame aparecem no início
    sem um cabeçalho explícito "EXAMINATION:", ainda assim devem ser
    rotuladas com section:"Examination". Isso inclui descrições de exame que
    identificam o tipo de estudo de imagem realizado.

    Reconheça sempre o conteúdo que descreve o exame e use
    section:"Examination", independentemente de haver ou não cabeçalho
    explícito.

    Essa abordagem estruturada melhora a organização e a legibilidade.

    ### Ponto crítico para findings_suffix:
    NÃO inclua cabeçalhos como "IMPRESSION:", "CONCLUSION:", etc. em
    extraction_text. Extraia apenas o conteúdo que vem após esses cabeçalhos.
    O sistema de formatação adicionará os cabeçalhos apropriados
    automaticamente.

    **Exemplo:** Se o texto contiver "IMPRESSION: 1. Severe arthritis. 2.
    Labral tear.", extraia apenas "1. Severe arthritis. 2. Labral tear." em
    extraction_text.

    ### Notas adicionais para findings_body:
    - Se uma mesma frase mencionar múltiplas estruturas com um mesmo status
      (por exemplo, "fígado, vesícula biliar e baço sem alterações"), divida
      em linhas de extração separadas, cada uma referenciando a estrutura
      relevante.
    - Se o texto mencionar subcabeçalhos como "CT ABDOMEN" ou
      "CERVICAL SPINE", só crie/mantenha esse subcabeçalho se ele organizar
      claramente vários achados de órgãos/estruturas. Não force subcabeçalhos
      se apenas 1 ou 2 linhas pertencerem a ele. Idealmente, um subcabeçalho
      deve agrupar 3+ seções para ser útil.

    ### Orientação especial para laudos de coluna:
    - Para exames de coluna (RM, TC), organize os achados por nível
      anatômico usando o formato: "Lumbar Spine Levels: L1-L2",
      "Lumbar Spine Levels: L2-L3", "Cervical Spine Levels: C5-C6", etc.
    - Separe achados gerais da coluna (alinhamento, lordose, altura dos
      corpos vertebrais) dos achados específicos por nível
    - Use seções dedicadas para: "Spinal Cord", "Bones" (lesões ósseas/
      medulares), "Paraspinal Soft Tissues" (músculos e partes moles)
    - Cada nível da coluna deve ter sua própria seção quando os achados forem
      descritos nível a nível
    - Essa organização por nível é preferível a um rótulo genérico "Spine"
      para utilidade clínica.

    ### Achados esqueléticos fora da coluna:
    Para achados esqueléticos que não sejam de coluna, agrupe-os em uma
    única seção como "Bones". Só mantenha lateralidade (Direito/Esquerdo)
    se houver simetria relevante nos achados.

    ## Formato JSON Obrigatório

    Cada resposta final deve ser um JSON válido com a chave de array
    "extractions". Cada "extraction" é um objeto com:

    ```json
    {{
      "text": "...",
      "category": "findings_prefix" | "findings_body" | "findings_suffix",
      "attributes": {{}}
    }}
    ```

    Dentro de "attributes", cada atributo deve ser um par chave-valor, como
    mostrado nos exemplos abaixo. O atributo **"clinical_significance"**
    DEVE ser incluído para extrações findings_body e deve ser um dos valores:
    **"normal"**, **"minor"**, **"significant"** ou **"not_applicable"**, para
    indicar a importância do achado.

    Níveis de significância clínica:
    - **"significant"**: Achados que exigem atenção médica, seguimento ou
      intervenção. Qualquer achado que tipicamente demande estudo de
      acompanhamento ou correlação clínica deve ser marcado como significant.
    - **"minor"**: Achados benignos ou incidentais, sem impacto clínico
      imediato e que não exigem seguimento.
    - **"normal"**: Ausência de anormalidades relevantes.
    - **"not_applicable"**: Quando não for possível determinar a
      significância.

    **Importante**: A significância clínica deve ser baseada apenas no
    conteúdo médico, não em qualidade de texto ou gramática. Pequenos erros de
    grafia ou gramática na entrada não devem influenciar a classificação da
    significância.

    ---

    # Few-Shot Examples

    Os exemplos a seguir demonstram como estruturar corretamente diferentes
    tipos de laudos radiológicos:

    {examples}

    {inference_section}
    """
).strip()
