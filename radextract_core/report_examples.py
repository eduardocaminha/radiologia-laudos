"""Exemplos de laudos radiológicos para treino do modelo de estruturação.

Este módulo contém exemplos curados de laudos radiológicos com suas
extrações estruturadas correspondentes. Esses exemplos são usados em
few-shot learning com o LangExtract para treinar o modelo na categorização
correta das seções do laudo em componentes de prefixo, corpo e sufixo,
com rótulos apropriados de significância clínica.

Os exemplos cobrem várias modalidades de imagem, incluindo TC, RM e diferentes
regiões anatômicas (coluna, abdome, encéfalo, joelho), oferecendo uma
cobertura abrangente para a tarefa de estruturação de laudos radiológicos.
"""

import textwrap
from enum import Enum

import langextract as lx


class ReportSectionType(Enum):
    PREFIX = "findings_prefix"
    BODY = "findings_body"
    SUFFIX = "findings_suffix"


def get_examples_for_model() -> list[lx.data.ExampleData]:
    """Examples that structure radiology reports into semantic sections.

    Returns:
        List of ExampleData objects containing radiology report examples
        with their corresponding structured extractions for training
        the language model.
    """
    return [
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                EXAME: TC DE ABDOME E PELVE COM CONTRASTE IV
                INDICAÇÃO CLÍNICA: Dor abdominal.
                COMPARAÇÃO: Sem exames prévios para comparação.
                TÉCNICA: Imagens axiais de abdome e pelve obtidas após administração de contraste intravenoso. Reconstruções coronais e sagitais avaliadas.

                ACHADOS:
                Não há alterações agudas nas bases pulmonares incluídas no exame. O fígado apresenta dimensões e contornos preservados. Há lesão hipodensa simples medindo 1,2 cm no segmento hepático VII, compatível com cisto. A vesícula biliar contém múltiplos cálculos calcificados, compatíveis com colelitíase.

                IMPRESSÃO:
                1. Colelitíase, sem sinais de colecistite aguda.
                2. Cisto hepático.
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="EXAME: TC DE ABDOME E PELVE COM CONTRASTE IV",
                    extraction_class="findings_prefix",
                    attributes={
                        "section": "Exame",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="INDICAÇÃO CLÍNICA: Dor abdominal.",
                    extraction_class="findings_prefix",
                    attributes={
                        "section": "Indicação Clínica",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="COMPARAÇÃO: Sem exames prévios para comparação.",
                    extraction_class="findings_prefix",
                    attributes={
                        "section": "Comparação",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="TÉCNICA: Imagens axiais de abdome e pelve obtidas após administração de contraste intravenoso. Reconstruções coronais e sagitais avaliadas.",
                    extraction_class="findings_prefix",
                    attributes={
                        "section": "Técnica",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Não há alterações agudas nas bases pulmonares incluídas no exame.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Pulmões",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O fígado apresenta dimensões e contornos preservados.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Fígado",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Lesão hipodensa simples medindo 1,2 cm no segmento hepático VII, compatível com cisto.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Fígado",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="A vesícula biliar contém múltiplos cálculos calcificados, compatíveis com colelitíase.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Vesícula Biliar",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="1. Colelitíase, sem sinais de colecistite aguda.\n2. Cisto hepático.",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                HISTÓRICO CLÍNICO:
                Dor lombar, descartar hérnia discal

                RM COLUNA LOMBAR SEM CONTRASTE:

                ACHADOS:
                A lordose lombar está preservada. As alturas dos corpos vertebrais encontram‑se mantidas.
                
                Pequeno hemangioma é observado no corpo vertebral de L3.
                
                O cone medular termina em L1 e apresenta aspecto normal.
                
                Em L2-L3, há discreta desidratação discal, sem estenose significativa.
                
                Em L3-L4, pequena protrusão discal posterior causando discreto estreitamento do canal.
                
                Em L4-L5, volumosa hérnia discal posterior com acentuada estenose do canal vertebral e compressão radicular.
                
                Em L5-S1, discreta protrusão discal, sem estenose significativa.
                
                A musculatura paravertebral apresenta aspecto preservado.

                IMPRESSÃO:
                Volumosa hérnia discal L4-L5 com estenose importante.
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="HISTÓRICO CLÍNICO:\nDor lombar, descartar hérnia discal\n\nRM COLUNA LOMBAR SEM CONTRASTE:",
                    extraction_class="findings_prefix",
                    attributes={},
                ),
                lx.data.Extraction(
                    extraction_text="A lordose lombar está preservada. As alturas dos corpos vertebrais encontram‑se mantidas.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Coluna Lombar",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Pequeno hemangioma é observado no corpo vertebral de L3.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Ossos",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O cone medular termina em L1 e apresenta aspecto normal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Medula Espinal",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em L2-L3, há discreta desidratação discal, sem estenose significativa.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Lombar: L2-L3",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em L3-L4, pequena protrusão discal posterior causando discreto estreitamento do canal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Lombar: L3-L4",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em L4-L5, volumosa hérnia discal posterior com acentuada estenose do canal vertebral e compressão radicular.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Lombar: L4-L5",
                        "clinical_significance": "significant",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em L5-S1, discreta protrusão discal, sem estenose significativa.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Lombar: L5-S1",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="A musculatura paravertebral apresenta aspecto preservado.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Tecidos Moles Paravertebrais",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Volumosa hérnia discal L4-L5 com estenose importante.",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                INDICAÇÃO: 
                Dor cervical, radiculopatia

                RM COLUNA CERVICAL:

                ACHADOS:
                A lordose cervical está preservada. Não há fraturas ou colapsos dos corpos vertebrais.
                
                A medula espinal cervical apresenta sinal normal.
                
                Em C3-C4, não há doença discal ou estenose significativas.
                
                Em C4-C5, discreto complexo osteofitário discal com leve estreitamento foraminal.
                
                Em C5-C6, hérnia discal moderada com estenose moderada do canal vertebral.
                
                Em C6-C7, pequena protrusão discal sem estenose significativa.

                IMPRESSÃO:
                Hérnia discal moderada em C5-C6 com estenose.
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="INDICAÇÃO: \nDor cervical, radiculopatia\n\nRM COLUNA CERVICAL:",
                    extraction_class="findings_prefix",
                    attributes={},
                ),
                lx.data.Extraction(
                    extraction_text="A lordose cervical está preservada. Não há fraturas ou colapsos dos corpos vertebrais.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Coluna Cervical",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="A medula espinal cervical apresenta sinal normal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Medula Espinal",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em C3-C4, não há doença discal ou estenose significativas.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Cervical: C3-C4",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em C4-C5, discreto complexo osteofitário discal com leve estreitamento foraminal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Cervical: C4-C5",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em C5-C6, hérnia discal moderada com estenose moderada do canal vertebral.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Cervical: C5-C6",
                        "clinical_significance": "significant",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Em C6-C7, pequena protrusão discal sem estenose significativa.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Níveis da Coluna Cervical: C6-C7",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Hérnia discal moderada em C5-C6 com estenose.",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                TÉCNICA: 
                TC helicoidal multidetectores do abdome superior, das bases pulmonares às adrenais, com e sem contraste intravenoso.

                ACHADOS:
                FÍGADO/VESÍCULA BILIAR/BAÇO: O fígado apresenta aspecto normal. A parede da vesícula biliar é de aspecto normal. O baço apresenta dimensões normais.

                PÂNCREAS/ADRENAIS: Pâncreas e glândulas adrenais bilaterais sem alterações significativas.

                RETROPERITÔNIO: Sem linfonodomegalias. Sem coleções líquidas.

                IMPRESSÃO:
                TC de abdome dentro da normalidade.
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="TÉCNICA: \nTC helicoidal multidetectores do abdome superior, das bases pulmonares às adrenais, com e sem contraste intravenoso.",
                    extraction_class="findings_prefix",
                    attributes={},
                ),
                lx.data.Extraction(
                    extraction_text="O fígado apresenta aspecto normal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Fígado",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="A parede da vesícula biliar apresenta aspecto normal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Vesícula Biliar",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O baço apresenta dimensões normais.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Baço",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Pâncreas e glândulas adrenais bilaterais sem alterações significativas.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Pâncreas/Adrenais",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Sem linfonodomegalias.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Retroperitônio",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Sem coleções líquidas.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Retroperitônio",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="TC de abdome dentro da normalidade.",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                HISTÓRIA: 
                Dor em abdome inferior

                TC DE ABDOME/PELVES COM CONTRASTE:
                
                ACHADOS:
                FÍGADO: Múltiplas metástases hepáticas, medindo até 3,2 cm.
                
                RINS: Rim esquerdo com hidronefrose moderada. Rim direito de aspecto normal.
                
                LINFONODOS: Linfonodos retroperitoneais aumentados, o maior medindo 2,1 cm.

                IMPRESSÃO:
                1. Múltiplas metástases hepáticas
                2. Hidronefrose à esquerda  
                3. Linfonodomegalias retroperitoneais
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="HISTÓRIA: \nDor em abdome inferior\n\nTC DE ABDOME/PELVES COM CONTRASTE:",
                    extraction_class="findings_prefix",
                    attributes={},
                ),
                lx.data.Extraction(
                    extraction_text="Múltiplas metástases hepáticas, medindo até 3,2 cm.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Fígado",
                        "clinical_significance": "significant",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O rim esquerdo apresenta hidronefrose moderada.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Rins",
                        "clinical_significance": "significant",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O rim direito apresenta aspecto normal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Rins",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Linfonodos retroperitoneais aumentados, o maior medindo 2,1 cm.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Linfonodos",
                        "clinical_significance": "significant",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="1. Múltiplas metástases hepáticas\n2. Hidronefrose à esquerda  \n3. Linfonodomegalias retroperitoneais",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                EXAME:
                RM de encéfalo sem contraste

                HISTÓRIA CLÍNICA:
                Cefaleia

                ACHADOS:
                O parênquima encefálico apresenta sinal normal. Não há lesões expansivas identificadas.
                
                O sistema ventricular apresenta dimensões e configuração normais.
                
                Não há desvio de linha média.

                IMPRESSÃO:
                RM de encéfalo dentro da normalidade.
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="EXAME:\nRM de encéfalo sem contraste\n\nHISTÓRIA CLÍNICA:\nCefaleia",
                    extraction_class="findings_prefix",
                    attributes={},
                ),
                lx.data.Extraction(
                    extraction_text="O parênquima encefálico apresenta sinal normal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Parênquima Encefálico",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Não há lesões expansivas identificadas.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Parênquima Encefálico",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O sistema ventricular apresenta dimensões e configuração normais.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Sistema Ventricular",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Não há desvio de linha média.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Parênquima Encefálico",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="RM de encéfalo dentro da normalidade.",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                INDICAÇÃO:
                Dor em joelho direito

                RM DE JOELHO DIREITO:

                ACHADOS:
                MENISCOS: Há rotura complexa do menisco medial. O menisco lateral encontra-se preservado.

                LIGAMENTOS: O LCA apresenta rotura completa. LCP, LCM e LCL estão íntegros.

                OSSOS: Discreto edema de medula óssea no côndilo femoral medial.

                IMPRESSÃO:
                1. Rotura complexa do menisco medial
                2. Rotura completa do LCA
                3. Edema de medula óssea no côndilo femoral medial
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="INDICAÇÃO:\nDor em joelho direito\n\nRM DE JOELHO DIREITO:",
                    extraction_class="findings_prefix",
                    attributes={},
                ),
                lx.data.Extraction(
                    extraction_text="Há rotura complexa do menisco medial.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Meniscos",
                        "clinical_significance": "significant",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O menisco lateral encontra-se preservado.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Meniscos",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O LCA apresenta rotura completa.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Ligamentos",
                        "clinical_significance": "significant",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="LCP, LCM e LCL estão íntegros.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Ligamentos",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Discreto edema de medula óssea no côndilo femoral medial.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Ossos",
                        "clinical_significance": "minor",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="1. Rotura complexa do menisco medial\n2. Rotura completa do LCA\n3. Edema de medula óssea no côndilo femoral medial",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
        lx.data.ExampleData(
            text=textwrap.dedent(
                """\
                EXAME: TC DE TÓRAX
                
                ACHADOS:
                Os pulmoes estao limpos bilateralmente. O tamanho do coraçao é normal. Sem derrame pleural.

                IMPRESSÃO:
                TC de tórax dentro da normalidade.
                """
            ).rstrip(),
            extractions=[
                lx.data.Extraction(
                    extraction_text="EXAME: TC DE TÓRAX",
                    extraction_class="findings_prefix",
                    attributes={
                        "section": "Exame",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Os pulmões estão limpos bilateralmente.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Pulmões",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="O tamanho do coração é normal.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Coração",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="Sem derrame pleural.",
                    extraction_class="findings_body",
                    attributes={
                        "section": "Pleura",
                        "clinical_significance": "normal",
                    },
                ),
                lx.data.Extraction(
                    extraction_text="TC de tórax dentro da normalidade.",
                    extraction_class="findings_suffix",
                    attributes={},
                ),
            ],
        ),
    ]
