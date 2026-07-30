"""Duas funções puras: validação do nome mDNS e o destaque dos textos rápidos."""

import main


class TestNomeMdns:
    """Regra do 6a2b17c: nome de máquina no mDNS, um rótulo DNS válido."""

    def test_padrao_e_aceito(self):
        assert main.mdns_nome_valido("fs") is True

    def test_nomes_comuns_sao_aceitos(self):
        assert main.mdns_nome_valido("sala") is True
        assert main.mdns_nome_valido("escritorio-2") is True
        assert main.mdns_nome_valido("pc1") is True

    def test_hifen_nas_pontas_e_recusado(self):
        assert main.mdns_nome_valido("-sala") is False
        assert main.mdns_nome_valido("sala-") is False

    def test_maiuscula_espaco_e_ponto_sao_recusados(self):
        assert main.mdns_nome_valido("Sala") is False
        assert main.mdns_nome_valido("sala 2") is False
        assert main.mdns_nome_valido("sala.local") is False

    def test_vazio_e_recusado(self):
        assert main.mdns_nome_valido("") is False

    def test_limite_de_63_caracteres(self):
        assert main.mdns_nome_valido("a" * 63) is True
        assert main.mdns_nome_valido("a" * 64) is False

    def test_dominio_leva_ponto_final_e_host_nao(self):
        # O zeroconf exige o ponto final no campo 'server'; a tela mostra sem.
        assert main.obter_mdns_dominio().endswith(".local.")
        assert main.obter_mdns_host().endswith(".local")
        assert not main.obter_mdns_host().endswith(".local.")


class TestDestacarTexto:
    def test_html_do_usuario_e_escapado(self):
        saida = str(main.destacar_texto("<script>alert(1)</script>"))

        assert "<script>" not in saida
        assert "&lt;script&gt;" in saida

    def test_email_ganha_destaque(self):
        saida = str(main.destacar_texto("contato: pessoa@exemplo.com"))

        assert "destaque-email" in saida

    def test_valor_em_reais_ganha_destaque(self):
        saida = str(main.destacar_texto("total R$ 1.234,56"))

        assert "destaque-valor" in saida

    def test_cpf_e_cep_ganham_destaque(self):
        assert "destaque-cpf" in str(main.destacar_texto("123.456.789-00"))
        assert "destaque-cep" in str(main.destacar_texto("01234-567"))

    def test_quebra_de_linha_virou_br(self):
        saida = str(main.destacar_texto("linha um\nlinha dois"))

        assert "<br>" in saida
        assert "\n" not in saida
