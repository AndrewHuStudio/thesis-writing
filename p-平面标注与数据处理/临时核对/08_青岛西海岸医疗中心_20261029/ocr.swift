import Foundation
import Vision
import AppKit
let path=CommandLine.arguments[1]
let image=NSImage(contentsOfFile:path)!
var rect=CGRect(origin:.zero,size:image.size)
let cg=image.cgImage(forProposedRect:&rect,context:nil,hints:nil)!
let req=VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.recognitionLanguages=["zh-Hans","en-US"]
req.usesLanguageCorrection=false
try VNImageRequestHandler(cgImage:cg).perform([req])
let out=(req.results ?? []).compactMap { o -> [String:Any]? in
 guard let c=o.topCandidates(1).first else{return nil}
 return ["text":c.string,"confidence":c.confidence,"x":o.boundingBox.minX*Double(cg.width),"y":(1-o.boundingBox.maxY)*Double(cg.height),"w":o.boundingBox.width*Double(cg.width),"h":o.boundingBox.height*Double(cg.height)]
}
let data=try JSONSerialization.data(withJSONObject:out,options:[.prettyPrinted,.sortedKeys])
print(String(data:data,encoding:.utf8)!)
