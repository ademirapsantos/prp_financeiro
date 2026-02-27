class MobileSession {
  final String token;
  final String userName;
  final String email;

  const MobileSession({
    required this.token,
    required this.userName,
    required this.email,
  });
}

class DashboardData {
  final double totalPendenteCartoes;
  final double totalDespesasMes;
  final int competenciaAno;
  final int competenciaMes;
  final List<Map<String, dynamic>> proximosVencimentos;

  const DashboardData({
    required this.totalPendenteCartoes,
    required this.totalDespesasMes,
    required this.competenciaAno,
    required this.competenciaMes,
    required this.proximosVencimentos,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    final resumo = (json['resumo'] as Map<String, dynamic>? ?? {});
    final competencia = (json['competencia'] as Map<String, dynamic>? ?? {});
    return DashboardData(
      totalPendenteCartoes: (resumo['total_pendente_cartoes'] ?? 0).toDouble(),
      totalDespesasMes: (resumo['total_despesas_mes'] ?? 0).toDouble(),
      competenciaAno: int.tryParse((competencia['ano'] ?? DateTime.now().year).toString()) ?? DateTime.now().year,
      competenciaMes:
          int.tryParse((competencia['mes'] ?? DateTime.now().month).toString()) ?? DateTime.now().month,
      proximosVencimentos: List<Map<String, dynamic>>.from(
        (json['proximos_vencimentos'] as List? ?? []),
      ),
    );
  }
}

class MobileLancamento {
  final String id;
  final String tipo;
  final String descricao;
  final String data;
  final double valor;
  final String meio;

  const MobileLancamento({
    required this.id,
    required this.tipo,
    required this.descricao,
    required this.data,
    required this.valor,
    required this.meio,
  });

  factory MobileLancamento.fromJson(Map<String, dynamic> json) {
    return MobileLancamento(
      id: (json['id'] ?? '').toString(),
      tipo: (json['tipo'] ?? '').toString(),
      descricao: (json['descricao'] ?? '').toString(),
      data: (json['data'] ?? '').toString(),
      valor: (json['valor'] ?? 0).toDouble(),
      meio: (json['meio'] ?? '').toString(),
    );
  }
}
