import AppKit
import Vision
import Foundation
let folder = CommandLine.arguments[1]
for n in [1,2,3,5,6] {
 let file = String(format:"%@/照片_%02d_转正.png",folder,n)
 let url = URL(fileURLWithPath:file)
 let image = NSImage(contentsOf:url)!
 var rect = CGRect(origin:.zero,size:image.size)
 let cg = image.cgImage(forProposedRect:&rect,context:nil,hints:nil)!
 let request = VNRecognizeTextRequest()
 request.recognitionLevel = .accurate
 request.recognitionLanguages = ["zh-Hans","en-US"]
 request.usesLanguageCorrection = false
 try VNImageRequestHandler(cgImage:cg).perform([request])
 let rows = (request.results ?? []).map { ob -> [String:Any] in
 let c = ob.topCandidates(1).first!
 let b=ob.boundingBox
 return ["text":c.string,"confidence":c.confidence,"box":[b.minX*Double(cg.width),(1-b.maxY)*Double(cg.height),b.width*Double(cg.width),b.height*Double(cg.height)]]
 }
 let data = try JSONSerialization.data(withJSONObject:rows,options:[.prettyPrinted,.sortedKeys,.fragmentsAllowed])
 try data.write(to:URL(fileURLWithPath:String(format:"%@/OCR_%02d.json",folder,n)))
 print(n,rows.count)
}
