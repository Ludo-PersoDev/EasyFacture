import pdfMake from 'pdfmake/build/pdfmake'
import pdfFonts from 'pdfmake/build/vfs_fonts'

// Initialisation des polices
pdfMake.vfs = pdfFonts.pdfMake.vfs

export const generateDevisPdfBlob = (devisData) => {
  return new Promise((resolve) => {
    const docDefinition = {
      content: [
        { text: 'DEVIS', fontSize: 24, bold: true, alignment: 'right', color: '#1e3a8a' },
        { text: `N° ${devisData.numeroDevis}`, fontSize: 12, bold: true, alignment: 'right', color: '#0284c7', margin: [0, 0, 0, 20] },
        
        { text: 'DESTINATAIRE :', fontSize: 9, bold: true, color: '#1e3a8a' },
        { text: devisData.clientNom, fontSize: 11, bold: true, margin: [0, 0, 0, 20] },

        {
          table: {
            headerRows: 1,
            widths: ['*', 'auto', 'auto', 'auto'],
            body: [
              [
                { text: 'Désignation', bold: true, color: 'white', fillColor: '#1e3a8a' },
                { text: 'Qté', bold: true, color: 'white', fillColor: '#1e3a8a', alignment: 'right' },
                { text: 'P.U. HT', bold: true, color: 'white', fillColor: '#1e3a8a', alignment: 'right' },
                { text: 'Total HT', bold: true, color: 'white', fillColor: '#1e3a8a', alignment: 'right' }
              ],
              [
                devisData.description,
                { text: '1.00', alignment: 'right' },
                { text: `${devisData.montantHt.toFixed(2)} €`, alignment: 'right' },
                { text: `${devisData.montantHt.toFixed(2)} €`, bold: true, alignment: 'right' }
              ]
            ]
          },
          margin: [0, 0, 0, 20]
        },

        { text: `Total HT : ${devisData.montantHt.toFixed(2)} €`, alignment: 'right' },
        { text: `Total TVA : ${devisData.montantTva.toFixed(2)} €`, alignment: 'right' },
        { text: `Total TTC : ${devisData.montantTtc.toFixed(2)} €`, fontSize: 12, bold: true, color: '#1e3a8a', alignment: 'right', margin: [0, 5, 0, 0] }
      ],
      defaultStyle: {
        font: 'Helvetica',
        fontSize: 10
      }
    }

    pdfMake.createPdf(docDefinition).getBlob((blob) => {
      resolve(blob)
    })
  })
}