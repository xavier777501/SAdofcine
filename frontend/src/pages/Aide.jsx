import PageHeader from '../components/PageHeader'

const SECTIONS = [
  {
    titre: 'Tableau de bord',
    resume: "La première chose à regarder chaque matin.",
    texte: [
      "En haut, cinq chiffres : combien de produits sont en rupture, combien sont sous le seuil critique, combien sont à commander bientôt, la valeur de votre prochaine commande (avec le plafond de budget appliqué si vous en avez fixé un), et l'argent que vous pourriez libérer en réduisant un stock excédentaire.",
      "En dessous, un rappel produit par produit de ce qui s'est vendu le mois dernier, pour repérer d'un coup d'œil ce qui part vite ou ce qui ne bouge plus.",
    ],
  },
  {
    titre: "Liste d'action",
    resume: "La liste détaillée de tout ce qu'il faut commander, dans l'ordre d'urgence.",
    texte: [
      "Seuls les produits qui ont besoin d'une action apparaissent ici — jamais ceux qui sont dans une situation normale.",
      "Classée du plus urgent (rupture) au moins urgent (à commander bientôt), avec pour chaque produit la quantité exacte à commander et sa valeur en FCFA. Vous pouvez filtrer par statut ou par classe (A, B, C) pour vous concentrer sur ce qui compte le plus.",
      "Si vous avez fixé un plafond de budget dans les Réglages, la liste se sépare en deux : ce qui rentre dans le budget, et ce qui est reporté à la prochaine commande faute d'argent disponible (repéré par le bandeau \"HORS PLAFOND\" ou la mention \"reportée\"). Vous pouvez toujours forcer l'inclusion d'un produit reporté si vous jugez que c'est nécessaire — vous gardez la main.",
      "Vous pouvez l'exporter en PDF ou en Excel pour l'emmener ou l'envoyer au moment de passer votre commande.",
    ],
  },
  {
    titre: 'Quoi commander',
    resume: "La version simplifiée : que commander, et surtout, quoi ne pas commander.",
    texte: [
      "Un encart rouge en haut signale vos produits importants (vos plus gros vendeurs) qui sont en rupture ou presque et que vous risquez de rater. Il estime ce que ça vous coûte de ne pas les commander, et un bouton vous permet de les ajouter directement à votre liste de commande.",
      "En dessous, d'un côté les produits à commander en priorité — un raccourci vers la liste d'action complète.",
      "De l'autre, les produits qu'il ne faut surtout pas recommander maintenant : soit parce que vous en avez déjà plus que nécessaire, soit parce qu'ils ne se vendent presque plus. Chaque ligne indique le montant d'argent immobilisé inutilement sur ce produit.",
    ],
  },
  {
    titre: 'Résumé des commandes',
    resume: "Un rappel produit par produit de vos ventes du mois dernier.",
    texte: [
      "Contrairement à la liste d'action, ici tous les produits apparaissent — même ceux dont le stock est normal — pour que vous puissiez vérifier n'importe quelle référence.",
      "Vous pouvez rechercher un produit par son nom ou son code, et filtrer par statut (rupture, critique, à commander, ou normal).",
    ],
  },
  {
    titre: 'Stock',
    resume: "La fiche complète de chaque produit de votre pharmacie.",
    texte: [
      "La liste entière de vos références, avec pour chacune : sa vitesse de rotation (rapide, lente, rare), sa priorité, ses ventes moyennes par mois, et ses seuils de commande.",
      "C'est ici que vous indiquez, produit par produit, s'il est vital, essentiel ou juste souhaitable pour votre pharmacie — ce réglage influence directement les recommandations.",
    ],
  },
  {
    titre: 'Importer',
    resume: "Où vous déposez vos fichiers pour que l'application reste à jour.",
    texte: [
      "Deux options, pour deux usages différents — vous choisissez laquelle à chaque fois :",
      "« Mettre à jour l'historique mensuel » — sert uniquement à calibrer la précision du moteur de calcul (ventes moyennes, seuils, priorités), jamais à passer une commande. Au départ, il faut importer vos 12 derniers mois un par un (un fichier par mois). Ensuite, un seul fichier par mois suffit : le mois le plus ancien sort automatiquement et le nouveau entre.",
      "« Préparer ma commande » — à chaque fois que vous voulez passer une commande, avec l'export Logpharma du moment. Ça met à jour votre stock actuel et recalcule instantanément ce qu'il faut commander. Vous pouvez cocher « Limiter cette commande aux références importées » si vous voulez ne travailler que sur les produits de ce fichier précis (utile pour une commande rapide et ciblée) — décochée, l'appli prend en compte tout votre stock comme d'habitude.",
    ],
  },
  {
    titre: 'Réglages',
    resume: "Ce qu'on configure une fois, et qu'on ne retouche presque jamais.",
    texte: [
      "Les délais de livraison de vos fournisseurs, selon le circuit (local, import...).",
      "Le rythme auquel vous préférez passer vos commandes (tous les jours, tous les 10 jours, ou une fois par mois).",
      "Le niveau de service que vous souhaitez pour chaque catégorie de produit — plus il est élevé, moins vous risquez la rupture, mais plus vous immobilisez de stock.",
      "Un plafond de budget (en FCFA) pour vos commandes, si vous voulez limiter ce que vous dépensez à chaque fois — laissez-le vide pour ne rien limiter.",
    ],
  },
]

export default function Aide() {
  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-3xl mx-auto space-y-6">
      <PageHeader
        label="Aide"
        title="Comprendre l'application"
        subtitle="À quoi sert chaque écran, en quelques mots simples."
      />

      <div className="space-y-4">
        {SECTIONS.map((section) => (
          <div
            key={section.titre}
            className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 p-6"
          >
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">{section.titre}</h2>
            <p className="mt-1 text-sm font-medium text-brand-dark dark:text-brand">{section.resume}</p>
            <div className="mt-3 space-y-2">
              {section.texte.map((paragraphe, i) => (
                <p key={i} className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  {paragraphe}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
