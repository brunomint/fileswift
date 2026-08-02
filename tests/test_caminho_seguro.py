"""Path traversal: resolver_caminho_seguro devolve None quando o caminho tenta
sair da pasta base. Regressão do 6a2b17c."""

import os

import main


def test_caminho_vazio_devolve_a_propria_base():
    base = os.path.realpath(main.MEDIA_FOLDER)
    assert main.resolver_caminho_seguro("") == base
    assert main.resolver_caminho_seguro(None) == base


def test_subpasta_normal_e_aceita():
    resolvido = main.resolver_caminho_seguro("uploads")
    assert resolvido is not None
    assert resolvido.startswith(os.path.realpath(main.MEDIA_FOLDER) + os.sep)


def test_pontos_duplos_sao_recusados():
    assert main.resolver_caminho_seguro("..") is None
    assert main.resolver_caminho_seguro("../..") is None
    assert main.resolver_caminho_seguro("uploads/../../..") is None


def test_caminho_absoluto_e_recusado():
    # os.path.join descarta a base quando o segundo pedaço é absoluto, então
    # sem a checagem isso viraria uma leitura de /etc/passwd.
    assert main.resolver_caminho_seguro("/etc/passwd") is None


def test_base_alternativa_e_respeitada(tmp_path):
    dentro = tmp_path / "documento.pdf"
    dentro.write_text("x")

    assert main.resolver_caminho_seguro("documento.pdf", base=str(tmp_path)) == str(
        dentro
    )
    assert main.resolver_caminho_seguro("../fora.pdf", base=str(tmp_path)) is None
